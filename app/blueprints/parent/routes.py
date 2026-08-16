import os

from flask import abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from app import constants
from app.blueprints.parent import parent_bp
from app.extensions import db
from app.models import Convocation, CourseMaterial, Document, Enrollment, Homework, Receipt, ReportCard, Schedule
from app.services.attendance import student_attendance_summary
from app.services.audit import log_action
from app.services.finance import student_balance
from app.services.grades import student_overall_average, student_subject_averages
from app.services.pdf import bulletin_pdf_path, generate_and_save_bulletin, generate_and_save_receipt, receipt_pdf_path
from app.services.permissions import require_permission, scoped_children_for, sidebar_items_for


def _own_child_or_403(student_id):
    children = {c.id: c for c in scoped_children_for(current_user)}
    student = children.get(student_id)
    if not student:
        abort(403)
    return student


@parent_bp.route("/")
@require_permission(constants.DASHBOARD_PARENT)
def dashboard():
    children = scoped_children_for(current_user)
    attendance_by_child = {}
    balance_by_child = {}
    for child in children:
        enrollment = Enrollment.query.filter_by(student_profile_id=child.id, status=Enrollment.STATUS_ACTIF).first()
        if enrollment:
            attendance_by_child[child.id] = student_attendance_summary(child.id, enrollment.school_year_id)
            due, paid, balance = student_balance(child, enrollment.school_year)
            balance_by_child[child.id] = {"due": due, "paid": paid, "balance": balance}

    return render_template(
        "dashboard/parent/dashboard.html",
        sidebar_items=sidebar_items_for(current_user),
        children=children,
        attendance_by_child=attendance_by_child,
        balance_by_child=balance_by_child,
    )


@parent_bp.route("/enfants/<int:student_id>/notes")
@require_permission(constants.DASHBOARD_PARENT)
def child_notes(student_id):
    student = _own_child_or_403(student_id)

    enrollment = Enrollment.query.filter_by(student_profile_id=student.id, status=Enrollment.STATUS_ACTIF).first()
    selected_term = request.args.get("term") or constants.TERM_T1
    if selected_term not in constants.TERMS:
        abort(400)

    subject_averages = []
    overall = None
    report_card = None
    if enrollment:
        subject_averages = student_subject_averages(student.id, enrollment.school_year_id, selected_term)
        overall = student_overall_average(student.id, enrollment.school_year_id, selected_term)
        report_card = ReportCard.query.filter_by(
            student_profile_id=student.id, school_year_id=enrollment.school_year_id, term=selected_term
        ).first()

    return render_template(
        "dashboard/parent/child_notes.html",
        sidebar_items=sidebar_items_for(current_user),
        student=student,
        subject_averages=subject_averages,
        overall_average=overall,
        selected_term=selected_term,
        report_card=report_card,
    )


@parent_bp.route("/enfants/bulletins/<int:report_card_id>.pdf")
@require_permission(constants.DASHBOARD_PARENT)
def bulletin_download(report_card_id):
    report_card = ReportCard.query.get_or_404(report_card_id)
    student = _own_child_or_403(report_card.student_profile_id)

    path = bulletin_pdf_path(report_card)
    if not os.path.exists(path):
        subject_averages = student_subject_averages(
            report_card.student_profile_id, report_card.school_year_id, report_card.term
        )
        overall = student_overall_average(report_card.student_profile_id, report_card.school_year_id, report_card.term)
        generate_and_save_bulletin(
            report_card, student, current_user.school, report_card.school_year, subject_averages, overall
        )
    return send_file(path, mimetype="application/pdf", download_name=f"bulletin-{student.matricule}.pdf")


@parent_bp.route("/enfants/recus/<int:receipt_id>.pdf")
@require_permission(constants.DASHBOARD_PARENT)
def receipt_download(receipt_id):
    receipt = Receipt.query.get_or_404(receipt_id)
    student = _own_child_or_403(receipt.payment.student_profile_id)

    path = receipt_pdf_path(receipt.number)
    if not os.path.exists(path):
        generate_and_save_receipt(receipt.payment, receipt, current_user.school)
    return send_file(path, mimetype="application/pdf", download_name=f"{receipt.number}.pdf")


@parent_bp.route("/enfants/<int:student_id>/emploi-du-temps")
@require_permission(constants.DASHBOARD_PARENT)
def child_schedule(student_id):
    student = _own_child_or_403(student_id)

    entries = []
    enrollment = Enrollment.query.filter_by(student_profile_id=student.id, status=Enrollment.STATUS_ACTIF).first()
    if enrollment:
        entries = Schedule.query.filter_by(
            classe_id=enrollment.classe_id, school_year_id=enrollment.school_year_id
        ).all()
        entries.sort(key=lambda s: (Schedule.DAY_ORDER[s.day], s.start_time))

    return render_template(
        "dashboard/parent/child_schedule.html",
        sidebar_items=sidebar_items_for(current_user),
        student=student,
        entries=entries,
        day_labels=Schedule.DAY_LABELS,
    )


@parent_bp.route("/enfants/<int:student_id>/convocations")
@require_permission(constants.DASHBOARD_PARENT)
def child_convocations(student_id):
    student = _own_child_or_403(student_id)
    if not current_user.parent_profile:
        abort(403)

    convocations = Convocation.query.filter_by(
        student_profile_id=student.id, parent_profile_id=current_user.parent_profile.id
    ).order_by(Convocation.date.desc()).all()

    # Le parent qui consulte la page "voit" la convocation : on transite envoyée -> vue.
    changed = False
    for convocation in convocations:
        if convocation.status == Convocation.STATUS_ENVOYEE:
            convocation.status = Convocation.STATUS_VUE
            changed = True
    if changed:
        db.session.commit()

    return render_template(
        "dashboard/parent/child_convocations.html",
        sidebar_items=sidebar_items_for(current_user),
        student=student,
        convocations=convocations,
    )


@parent_bp.route("/convocations/<int:convocation_id>/confirmer", methods=["POST"])
@require_permission(constants.DASHBOARD_PARENT)
def convocation_confirm(convocation_id):
    convocation = Convocation.query.get_or_404(convocation_id)
    if not current_user.parent_profile or convocation.parent_profile_id != current_user.parent_profile.id:
        abort(403)

    if convocation.status in (Convocation.STATUS_VUE, Convocation.STATUS_ENVOYEE, Convocation.STATUS_CREEE):
        convocation.status = Convocation.STATUS_CONFIRMEE
        db.session.commit()
        log_action("convocation_confirmed", entity_type="Convocation", entity_id=convocation.id)
        flash("Présence confirmée.", "info")

    return redirect(url_for("parent.child_convocations", student_id=convocation.student_profile_id))


@parent_bp.route("/enfants/<int:student_id>/bibliotheque")
@require_permission(constants.DASHBOARD_PARENT)
def child_library(student_id):
    student = _own_child_or_403(student_id)

    materials, homeworks = [], []
    files_by_material, files_by_homework = {}, {}
    enrollment = Enrollment.query.filter_by(student_profile_id=student.id, status=Enrollment.STATUS_ACTIF).first()
    if enrollment:
        materials = (
            CourseMaterial.query.filter_by(classe_id=enrollment.classe_id, school_year_id=enrollment.school_year_id)
            .order_by(CourseMaterial.created_at.desc())
            .all()
        )
        homeworks = (
            Homework.query.filter_by(classe_id=enrollment.classe_id, school_year_id=enrollment.school_year_id)
            .order_by(Homework.due_date.desc())
            .all()
        )
        files_by_material = {
            d.owner_id: d
            for d in Document.query.filter_by(owner_type="CourseMaterial", category="file").all()
            if d.owner_id in {m.id for m in materials}
        }
        files_by_homework = {
            d.owner_id: d
            for d in Document.query.filter_by(owner_type="Homework", category="file").all()
            if d.owner_id in {h.id for h in homeworks}
        }

    return render_template(
        "dashboard/parent/child_library.html",
        sidebar_items=sidebar_items_for(current_user),
        student=student,
        materials=materials,
        homeworks=homeworks,
        files_by_material=files_by_material,
        files_by_homework=files_by_homework,
    )


@parent_bp.route("/enfants/<int:student_id>/bibliotheque/fichiers/<int:document_id>")
@require_permission(constants.DASHBOARD_PARENT)
def child_library_file_download(student_id, document_id):
    student = _own_child_or_403(student_id)
    enrollment = Enrollment.query.filter_by(student_profile_id=student.id, status=Enrollment.STATUS_ACTIF).first()
    if not enrollment:
        abort(403)

    document = Document.query.get_or_404(document_id)
    if document.owner_type == "CourseMaterial":
        owner = CourseMaterial.query.get_or_404(document.owner_id)
    elif document.owner_type == "Homework":
        owner = Homework.query.get_or_404(document.owner_id)
    else:
        abort(404)

    if owner.classe_id != enrollment.classe_id or owner.school_year_id != enrollment.school_year_id:
        abort(403)
    if not os.path.exists(document.file_path):
        abort(404)
    return send_file(document.file_path, mimetype=document.mime_type, download_name=document.original_filename)
