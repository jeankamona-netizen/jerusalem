import datetime
import os
from decimal import Decimal

from flask import Response, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from app import constants
from app.blueprints.prefet import prefet_bp
from app.blueprints.prefet.forms import AnnouncementForm, EventForm
from app.extensions import db
from app.models import Announcement, Application, Classe, Document, Event, StudentProfile, TeacherProfile
from app.models.mixins import utcnow
from app.services.admissions import accept_application
from app.services.attendance import daily_school_stats
from app.services.audit import log_action
from app.services.finance import active_students_query, student_balance
from app.services.pdf import render_pdf
from app.services.permissions import require_permission, sidebar_items_for
from app.services.reports import academic_report, attendance_report, financial_report
from app.services.school_year import get_current_school_year
from app.services.uploads import UploadError, validate_and_save_upload


@prefet_bp.route("/")
@require_permission(constants.DASHBOARD_PREFET)
def dashboard():
    stats = {
        "eleves": StudentProfile.query.filter_by(deleted_at=None).count(),
        "enseignants": TeacherProfile.query.filter_by(deleted_at=None).count(),
        "classes": Classe.query.count(),
        "preinscriptions_en_attente": Application.query.filter_by(status=Application.STATUS_SOUMIS).count(),
    }
    school_year = get_current_school_year(current_user.school_id)
    attendance_stats = daily_school_stats(school_year, datetime.date.today()) if school_year else None

    return render_template(
        "dashboard/prefet/dashboard.html",
        sidebar_items=sidebar_items_for(current_user),
        stats=stats,
        attendance_stats=attendance_stats,
    )


@prefet_bp.route("/finance")
@require_permission(constants.FINANCE_VIEW_GLOBAL)
def finance():
    """Vue globale en lecture seule (brief section 8) : le Préfet consulte, il ne modifie
    jamais une opération comptable ici — aucune action d'écriture sur cette page."""
    school_year = get_current_school_year(current_user.school_id)
    totals = {"due": Decimal("0"), "paid": Decimal("0"), "balance": Decimal("0")}

    if school_year:
        for student in active_students_query(school_year):
            due, paid, balance = student_balance(student, school_year)
            totals["due"] += due
            totals["paid"] += paid
            totals["balance"] += balance

    return render_template(
        "dashboard/prefet/finance.html",
        sidebar_items=sidebar_items_for(current_user),
        totals=totals,
        school_year=school_year,
    )


@prefet_bp.route("/preinscriptions")
@require_permission(constants.APPLICATIONS_MANAGE)
def applications():
    status_filter = request.args.get("status")
    if status_filter and status_filter not in Application.STATUS_CHOICES:
        abort(400)

    query = Application.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    applications_list = query.order_by(Application.created_at.desc()).all()

    return render_template(
        "dashboard/prefet/applications.html",
        sidebar_items=sidebar_items_for(current_user),
        applications=applications_list,
        selected_status=status_filter,
    )


@prefet_bp.route("/preinscriptions/<int:application_id>")
@require_permission(constants.APPLICATIONS_MANAGE)
def application_detail(application_id):
    application = Application.query.get_or_404(application_id)
    documents = Document.query.filter_by(owner_type="Application", owner_id=application.id).all()
    return render_template(
        "dashboard/prefet/application_detail.html",
        sidebar_items=sidebar_items_for(current_user),
        application=application,
        documents=documents,
    )


@prefet_bp.route("/preinscriptions/documents/<int:document_id>")
@require_permission(constants.APPLICATIONS_MANAGE)
def application_document(document_id):
    document = Document.query.get_or_404(document_id)
    if not os.path.exists(document.file_path):
        abort(404)
    return send_file(document.file_path, mimetype=document.mime_type, download_name=document.original_filename)


@prefet_bp.route("/preinscriptions/<int:application_id>/statut", methods=["POST"])
@require_permission(constants.APPLICATIONS_MANAGE)
def application_set_status(application_id):
    application = Application.query.get_or_404(application_id)
    new_status = request.form.get("status")
    if new_status not in (Application.STATUS_EN_EXAMEN, Application.STATUS_INCOMPLET):
        abort(400)

    application.status = new_status
    application.decision_comment = request.form.get("comment", "").strip() or None
    db.session.commit()
    log_action("application_status_changed", entity_type="Application", entity_id=application.id, new_value=new_status)
    flash("Statut du dossier mis à jour.", "info")
    return redirect(url_for("prefet.application_detail", application_id=application.id))


@prefet_bp.route("/preinscriptions/<int:application_id>/accepter", methods=["POST"])
@require_permission(constants.APPLICATIONS_MANAGE)
def application_accept(application_id):
    application = Application.query.get_or_404(application_id)
    if application.status == Application.STATUS_ACCEPTE:
        flash("Ce dossier a déjà été accepté.", "error")
        return redirect(url_for("prefet.application_detail", application_id=application.id))

    try:
        student = accept_application(application, current_user, comment=request.form.get("comment", "").strip() or None)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("prefet.application_detail", application_id=application.id))

    db.session.commit()
    log_action("application_accepted", entity_type="Application", entity_id=application.id, new_value=student.id)
    flash(f"Dossier accepté : {student.full_name} a été inscrit(e).", "info")
    return redirect(url_for("prefet.application_detail", application_id=application.id))


@prefet_bp.route("/preinscriptions/<int:application_id>/refuser", methods=["POST"])
@require_permission(constants.APPLICATIONS_MANAGE)
def application_refuse(application_id):
    application = Application.query.get_or_404(application_id)
    application.status = Application.STATUS_REFUSE
    application.decision_comment = request.form.get("comment", "").strip() or None
    application.decided_at = utcnow()
    application.decided_by_user_id = current_user.id
    db.session.commit()
    log_action("application_refused", entity_type="Application", entity_id=application.id)
    flash("Dossier refusé.", "info")
    return redirect(url_for("prefet.application_detail", application_id=application.id))


@prefet_bp.route("/actualites", methods=["GET", "POST"])
@require_permission(constants.CONTENT_MANAGE)
def content():
    announcement_form = AnnouncementForm()
    event_form = EventForm()

    if request.form.get("form_name") == "announcement" and announcement_form.validate_on_submit():
        announcement = Announcement(
            school_id=current_user.school_id,
            title=announcement_form.title.data.strip(),
            body=announcement_form.body.data.strip(),
            category=announcement_form.category.data,
            author_id=current_user.id,
        )
        db.session.add(announcement)
        db.session.flush()

        try:
            if announcement_form.image.data and announcement_form.image.data.filename:
                validate_and_save_upload(
                    announcement_form.image.data, "Announcement", announcement.id, "image", current_user.id
                )
        except UploadError as exc:
            db.session.rollback()
            flash(str(exc), "error")
            return redirect(url_for("prefet.content"))

        db.session.commit()
        log_action("announcement_created", entity_type="Announcement", entity_id=announcement.id)
        flash("Actualité créée en brouillon.", "info")
        return redirect(url_for("prefet.content"))

    if request.form.get("form_name") == "event" and event_form.validate_on_submit():
        event = Event(
            school_id=current_user.school_id,
            title=event_form.title.data.strip(),
            description=event_form.description.data.strip() if event_form.description.data else None,
            date=event_form.date.data,
            category=event_form.category.data,
            created_by_user_id=current_user.id,
        )
        db.session.add(event)
        db.session.flush()

        try:
            if event_form.image.data and event_form.image.data.filename:
                validate_and_save_upload(event_form.image.data, "Event", event.id, "image", current_user.id)
        except UploadError as exc:
            db.session.rollback()
            flash(str(exc), "error")
            return redirect(url_for("prefet.content"))

        db.session.commit()
        log_action("event_created", entity_type="Event", entity_id=event.id)
        flash("Événement créé.", "info")
        return redirect(url_for("prefet.content"))

    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    events = Event.query.order_by(Event.date.desc()).all()
    images_by_announcement = {
        d.owner_id: d
        for d in Document.query.filter_by(owner_type="Announcement", category="image").all()
    }
    images_by_event = {
        d.owner_id: d for d in Document.query.filter_by(owner_type="Event", category="image").all()
    }

    return render_template(
        "dashboard/prefet/content.html",
        sidebar_items=sidebar_items_for(current_user),
        announcement_form=announcement_form,
        event_form=event_form,
        announcements=announcements,
        events=events,
        images_by_announcement=images_by_announcement,
        images_by_event=images_by_event,
    )


@prefet_bp.route("/actualites/<int:announcement_id>/publier", methods=["POST"])
@require_permission(constants.CONTENT_MANAGE)
def announcement_publish(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    announcement.status = Announcement.STATUS_PUBLIE
    announcement.published_at = utcnow()
    db.session.commit()
    log_action("announcement_published", entity_type="Announcement", entity_id=announcement.id)
    flash("Actualité publiée.", "info")
    return redirect(url_for("prefet.content"))


@prefet_bp.route("/actualites/<int:announcement_id>/depublier", methods=["POST"])
@require_permission(constants.CONTENT_MANAGE)
def announcement_unpublish(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    announcement.status = Announcement.STATUS_BROUILLON
    db.session.commit()
    log_action("announcement_unpublished", entity_type="Announcement", entity_id=announcement.id)
    flash("Actualité repassée en brouillon.", "info")
    return redirect(url_for("prefet.content"))


@prefet_bp.route("/actualites/<int:announcement_id>/supprimer", methods=["POST"])
@require_permission(constants.CONTENT_MANAGE)
def announcement_delete(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    Document.query.filter_by(owner_type="Announcement", owner_id=announcement.id).delete()
    db.session.delete(announcement)
    db.session.commit()
    log_action("announcement_deleted", entity_type="Announcement", entity_id=announcement_id)
    flash("Actualité supprimée.", "info")
    return redirect(url_for("prefet.content"))


@prefet_bp.route("/evenements/<int:event_id>/supprimer", methods=["POST"])
@require_permission(constants.CONTENT_MANAGE)
def event_delete(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    log_action("event_deleted", entity_type="Event", entity_id=event_id)
    flash("Événement supprimé.", "info")
    return redirect(url_for("prefet.content"))


def _report_filters():
    """Période par défaut pour le rapport de présence : du début de l'année scolaire (ou du
    1er du mois si l'année n'a pas de date de début) à aujourd'hui — évite un rapport vide sur
    une plage de dates non choisie."""
    today = datetime.date.today()
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    try:
        date_from = datetime.date.fromisoformat(date_from) if date_from else today.replace(day=1)
    except ValueError:
        abort(400)
    try:
        date_to = datetime.date.fromisoformat(date_to) if date_to else today
    except ValueError:
        abort(400)
    term = request.args.get("term") or constants.TERM_T1
    if term not in constants.TERMS:
        abort(400)
    return date_from, date_to, term


@prefet_bp.route("/rapports")
@require_permission(constants.REPORTS_VIEW)
def reports():
    school_year = get_current_school_year(current_user.school_id)
    date_from, date_to, term = _report_filters()

    attendance_rows, financial, academic = [], None, None
    if school_year:
        attendance_rows = attendance_report(school_year, date_from, date_to)
        financial = financial_report(school_year)
        academic = academic_report(school_year, term)

    return render_template(
        "dashboard/prefet/reports.html",
        sidebar_items=sidebar_items_for(current_user),
        school_year=school_year,
        date_from=date_from,
        date_to=date_to,
        term=term,
        attendance_rows=attendance_rows,
        financial=financial,
        academic=academic,
    )


@prefet_bp.route("/rapports/presence.pdf")
@require_permission(constants.REPORTS_VIEW)
def report_attendance_pdf():
    school_year = get_current_school_year(current_user.school_id)
    if not school_year:
        abort(404)
    date_from, date_to, _term = _report_filters()
    rows = attendance_report(school_year, date_from, date_to)
    pdf_bytes = render_pdf(
        "pdf/report_attendance.html",
        school=current_user.school,
        school_year=school_year,
        date_from=date_from,
        date_to=date_to,
        rows=rows,
    )
    return Response(pdf_bytes, mimetype="application/pdf")


@prefet_bp.route("/rapports/finance.pdf")
@require_permission(constants.REPORTS_VIEW)
def report_financial_pdf():
    school_year = get_current_school_year(current_user.school_id)
    if not school_year:
        abort(404)
    report = financial_report(school_year)
    pdf_bytes = render_pdf(
        "pdf/report_financial.html",
        school=current_user.school,
        school_year=school_year,
        report=report,
    )
    return Response(pdf_bytes, mimetype="application/pdf")


@prefet_bp.route("/rapports/academique.pdf")
@require_permission(constants.REPORTS_VIEW)
def report_academic_pdf():
    school_year = get_current_school_year(current_user.school_id)
    if not school_year:
        abort(404)
    _date_from, _date_to, term = _report_filters()
    report = academic_report(school_year, term)
    pdf_bytes = render_pdf(
        "pdf/report_academic.html",
        school=current_user.school,
        school_year=school_year,
        term=term,
        term_label=constants.TERM_LABELS.get(term, term),
        report=report,
    )
    return Response(pdf_bytes, mimetype="application/pdf")
