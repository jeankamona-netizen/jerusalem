import os

from flask import Response, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from app import constants
from app.blueprints.direction_etudes import direction_etudes_bp
from app.blueprints.direction_etudes.forms import ScheduleForm
from app.extensions import db
from app.models import (
    Classe,
    CourseMaterial,
    Enrollment,
    Homework,
    Notification,
    ReportCard,
    Room,
    Schedule,
    StudentProfile,
    Subject,
    TeacherProfile,
)
from app.models.mixins import utcnow
from app.services.audit import log_action
from app.services.grades import student_overall_average, student_subject_averages
from app.services.notifications import notify
from app.services.pdf import bulletin_pdf_path, generate_and_save_bulletin, render_pdf
from app.services.permissions import require_permission, sidebar_items_for
from app.services.school_year import get_current_school_year
from app.services.schedule import check_conflicts


@direction_etudes_bp.route("/")
@require_permission(constants.DASHBOARD_DIRECTION_ETUDES)
def dashboard():
    school_year = get_current_school_year(current_user.school_id)
    stats = {
        "classes": Classe.query.count(),
        "matieres": Subject.query.count(),
        "creneaux": Schedule.query.filter_by(school_year_id=school_year.id).count() if school_year else 0,
    }
    return render_template(
        "dashboard/direction_etudes/dashboard.html",
        sidebar_items=sidebar_items_for(current_user),
        stats=stats,
    )


@direction_etudes_bp.route("/notes")
@require_permission(constants.GRADES_VIEW_ALL)
def grades_overview():
    classes = Classe.query.order_by(Classe.name).all()
    if not classes:
        return render_template(
            "dashboard/direction_etudes/grades_overview.html",
            sidebar_items=sidebar_items_for(current_user),
            classes=[],
            rows=[],
            selected_classe=None,
            selected_term=constants.TERM_T1,
        )

    classe_id = request.args.get("classe_id", type=int) or classes[0].id
    selected_classe = Classe.query.get_or_404(classe_id)
    selected_term = request.args.get("term") or constants.TERM_T1
    if selected_term not in constants.TERMS:
        abort(400)

    enrollments = Enrollment.query.filter_by(
        classe_id=selected_classe.id,
        school_year_id=selected_classe.school_year_id,
        status=Enrollment.STATUS_ACTIF,
    ).all()
    students = sorted((e.student for e in enrollments), key=lambda s: s.nom)

    rows = []
    for student in students:
        average = student_overall_average(student.id, selected_classe.school_year_id, selected_term)
        report_card = ReportCard.query.filter_by(
            student_profile_id=student.id, school_year_id=selected_classe.school_year_id, term=selected_term
        ).first()
        rows.append({"student": student, "average": average, "report_card": report_card})

    return render_template(
        "dashboard/direction_etudes/grades_overview.html",
        sidebar_items=sidebar_items_for(current_user),
        classes=classes,
        rows=rows,
        selected_classe=selected_classe,
        selected_term=selected_term,
    )


@direction_etudes_bp.route("/bulletins/<int:student_id>/<term>/generer", methods=["POST"])
@require_permission(constants.BULLETINS_GENERATE)
def generate_bulletin(student_id, term):
    if term not in constants.TERMS:
        abort(400)

    student = StudentProfile.query.get_or_404(student_id)
    enrollment = Enrollment.query.filter_by(student_profile_id=student.id, status=Enrollment.STATUS_ACTIF).first()
    if not enrollment:
        abort(404)
    school_year = enrollment.school_year

    report_card = ReportCard.query.filter_by(
        student_profile_id=student.id, school_year_id=school_year.id, term=term
    ).first()
    if not report_card:
        report_card = ReportCard(student_profile_id=student.id, school_year_id=school_year.id, term=term)
        db.session.add(report_card)

    report_card.generated_at = utcnow()
    report_card.status = ReportCard.STATUS_GENERATED
    db.session.flush()

    subject_averages = student_subject_averages(student.id, school_year.id, term)
    overall = student_overall_average(student.id, school_year.id, term)
    path = generate_and_save_bulletin(report_card, student, current_user.school, school_year, subject_averages, overall)
    report_card.pdf_path = path

    if student.user:
        notify(
            student.user,
            Notification.TYPE_RESULTAT,
            title=f"Bulletin disponible — {constants.TERM_LABELS.get(term, term)}",
            body=f"Moyenne générale : {overall:.2f}/20." if overall is not None else None,
            related_url=url_for("eleve.bulletin_download", report_card_id=report_card.id),
        )
    for parent in student.parents:
        notify(
            parent.user,
            Notification.TYPE_RESULTAT,
            title=f"Bulletin disponible — {student.full_name} ({constants.TERM_LABELS.get(term, term)})",
            body=f"Moyenne générale : {overall:.2f}/20." if overall is not None else None,
            related_url=url_for("parent.bulletin_download", report_card_id=report_card.id),
        )

    db.session.commit()

    log_action("bulletin_generated", entity_type="ReportCard", entity_id=report_card.id)
    flash(f"Bulletin généré pour {student.full_name}.", "info")
    return redirect(url_for("direction_etudes.grades_overview", classe_id=enrollment.classe_id, term=term))


@direction_etudes_bp.route("/bulletins/<int:report_card_id>.pdf")
@require_permission(constants.GRADES_VIEW_ALL)
def bulletin_download(report_card_id):
    report_card = ReportCard.query.get_or_404(report_card_id)
    path = bulletin_pdf_path(report_card)
    if not os.path.exists(path):
        subject_averages = student_subject_averages(
            report_card.student_profile_id, report_card.school_year_id, report_card.term
        )
        overall = student_overall_average(report_card.student_profile_id, report_card.school_year_id, report_card.term)
        generate_and_save_bulletin(
            report_card, report_card.student, current_user.school, report_card.school_year, subject_averages, overall
        )
    return send_file(path, mimetype="application/pdf", download_name=f"bulletin-{report_card.student.matricule}.pdf")


def _filtered_schedules(school_year_id):
    classe_id = request.args.get("classe_id", type=int)
    teacher_id = request.args.get("teacher_id", type=int)
    room_id = request.args.get("room_id", type=int)

    query = Schedule.query.filter_by(school_year_id=school_year_id)
    if classe_id:
        query = query.filter_by(classe_id=classe_id)
    if teacher_id:
        query = query.filter_by(teacher_profile_id=teacher_id)
    if room_id:
        query = query.filter_by(room_id=room_id)

    entries = query.all()
    entries.sort(key=lambda s: (Schedule.DAY_ORDER[s.day], s.start_time))
    return entries, classe_id, teacher_id, room_id


def _schedule_form_for(school_year):
    """Formulaire de création, choix peuplés — utilisé par la page (rendu, pour un manager)
    et par la route de création elle-même (validation du POST)."""
    form = ScheduleForm()
    form.classe_id.choices = [(c.id, c.name) for c in Classe.query.order_by(Classe.name).all()]
    form.subject_id.choices = [(s.id, s.name) for s in Subject.query.order_by(Subject.name).all()]
    form.teacher_profile_id.choices = [
        (t.id, t.nom) for t in TeacherProfile.query.order_by(TeacherProfile.nom).all()
    ]
    form.room_id.choices = [("", "— Aucune —")] + [
        (str(r.id), r.name) for r in Room.query.order_by(Room.name).all()
    ]
    return form


@direction_etudes_bp.route("/emploi-du-temps")
@require_permission(constants.SCHEDULE_VIEW_ALL)
def schedule_list():
    school_year = get_current_school_year(current_user.school_id)
    can_manage = current_user.has_permission(constants.SCHEDULE_MANAGE)

    form = _schedule_form_for(school_year) if (can_manage and school_year) else None

    entries, classe_id, teacher_id, room_id = ([], None, None, None)
    if school_year:
        entries, classe_id, teacher_id, room_id = _filtered_schedules(school_year.id)

    return render_template(
        "dashboard/direction_etudes/schedule_list.html",
        sidebar_items=sidebar_items_for(current_user),
        form=form,
        entries=entries,
        classes=Classe.query.order_by(Classe.name).all(),
        teachers=TeacherProfile.query.order_by(TeacherProfile.nom).all(),
        rooms=Room.query.order_by(Room.name).all(),
        selected_classe_id=classe_id,
        selected_teacher_id=teacher_id,
        selected_room_id=room_id,
        can_manage=can_manage,
        school_year=school_year,
    )


@direction_etudes_bp.route("/emploi-du-temps/creer", methods=["POST"])
@require_permission(constants.SCHEDULE_MANAGE)
def schedule_create():
    school_year = get_current_school_year(current_user.school_id)
    if not school_year:
        abort(400)

    form = _schedule_form_for(school_year)
    if not form.validate_on_submit():
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "error")
        return redirect(url_for("direction_etudes.schedule_list"))

    room_id = int(form.room_id.data) if form.room_id.data else None
    conflicts = check_conflicts(
        school_year_id=school_year.id,
        classe_id=form.classe_id.data,
        teacher_profile_id=form.teacher_profile_id.data,
        room_id=room_id,
        day=form.day.data,
        start_time=form.start_time.data,
        end_time=form.end_time.data,
    )
    if form.start_time.data >= form.end_time.data:
        conflicts.append("L'heure de fin doit être après l'heure de début.")

    if conflicts:
        for message in conflicts:
            flash(message, "error")
        return redirect(url_for("direction_etudes.schedule_list"))

    entry = Schedule(
        school_year_id=school_year.id,
        classe_id=form.classe_id.data,
        subject_id=form.subject_id.data,
        teacher_profile_id=form.teacher_profile_id.data,
        room_id=room_id,
        day=form.day.data,
        start_time=form.start_time.data,
        end_time=form.end_time.data,
    )
    db.session.add(entry)
    db.session.commit()
    log_action("schedule_created", entity_type="Schedule", entity_id=entry.id)
    flash("Créneau ajouté à l'emploi du temps.", "info")
    return redirect(url_for("direction_etudes.schedule_list"))


@direction_etudes_bp.route("/emploi-du-temps/<int:schedule_id>/supprimer", methods=["POST"])
@require_permission(constants.SCHEDULE_MANAGE)
def schedule_delete(schedule_id):
    entry = Schedule.query.get_or_404(schedule_id)
    db.session.delete(entry)
    db.session.commit()
    log_action("schedule_deleted", entity_type="Schedule", entity_id=schedule_id)
    flash("Créneau supprimé.", "info")
    return redirect(url_for("direction_etudes.schedule_list"))


@direction_etudes_bp.route("/emploi-du-temps/imprimer")
@require_permission(constants.SCHEDULE_VIEW_ALL)
def schedule_pdf():
    school_year = get_current_school_year(current_user.school_id)
    entries, classe_id, teacher_id, room_id = ([], None, None, None)
    title = "Emploi du temps"
    if school_year:
        entries, classe_id, teacher_id, room_id = _filtered_schedules(school_year.id)
        if classe_id:
            classe = Classe.query.get(classe_id)
            title = f"Emploi du temps — {classe.name}" if classe else title
        elif teacher_id:
            teacher = TeacherProfile.query.get(teacher_id)
            title = f"Emploi du temps — {teacher.nom}" if teacher else title
        elif room_id:
            room = Room.query.get(room_id)
            title = f"Emploi du temps — Salle {room.name}" if room else title

    pdf_bytes = render_pdf(
        "pdf/schedule.html",
        school=current_user.school,
        school_year=school_year,
        title=title,
        entries=entries,
        day_labels=Schedule.DAY_LABELS,
    )
    return Response(pdf_bytes, mimetype="application/pdf")


@direction_etudes_bp.route("/bibliotheque")
@require_permission(constants.LIBRARY_VIEW_ALL)
def library_overview():
    """Vue de supervision, lecture seule (brief : la Direction des Études consulte, jamais
    d'écriture — le dépôt de contenu reste la responsabilité de l'enseignant, même logique
    que pour les notes)."""
    classes = Classe.query.order_by(Classe.name).all()
    if not classes:
        return render_template(
            "dashboard/direction_etudes/library_overview.html",
            sidebar_items=sidebar_items_for(current_user),
            classes=[],
            selected_classe=None,
            materials=[],
            homeworks=[],
        )

    classe_id = request.args.get("classe_id", type=int) or classes[0].id
    selected_classe = Classe.query.get_or_404(classe_id)

    materials = (
        CourseMaterial.query.filter_by(classe_id=selected_classe.id, school_year_id=selected_classe.school_year_id)
        .order_by(CourseMaterial.created_at.desc())
        .all()
    )
    homeworks = (
        Homework.query.filter_by(classe_id=selected_classe.id, school_year_id=selected_classe.school_year_id)
        .order_by(Homework.due_date.desc())
        .all()
    )

    return render_template(
        "dashboard/direction_etudes/library_overview.html",
        sidebar_items=sidebar_items_for(current_user),
        classes=classes,
        selected_classe=selected_classe,
        materials=materials,
        homeworks=homeworks,
    )
