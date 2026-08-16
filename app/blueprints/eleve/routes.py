import os

from flask import abort, render_template, request, send_file
from flask_login import current_user

from app import constants
from app.blueprints.eleve import eleve_bp
from app.models import CourseMaterial, Document, Enrollment, Homework, ReportCard, Schedule
from app.services.attendance import student_attendance_summary
from app.services.grades import student_overall_average, student_subject_averages
from app.services.pdf import bulletin_pdf_path, generate_and_save_bulletin
from app.services.permissions import require_permission, scoped_own_student_profile, sidebar_items_for


@eleve_bp.route("/")
@require_permission(constants.DASHBOARD_ELEVE)
def dashboard():
    student = scoped_own_student_profile(current_user)
    attendance_summary = None
    if student:
        enrollment = Enrollment.query.filter_by(student_profile_id=student.id, status=Enrollment.STATUS_ACTIF).first()
        if enrollment:
            attendance_summary = student_attendance_summary(student.id, enrollment.school_year_id)

    return render_template(
        "dashboard/eleve/dashboard.html",
        sidebar_items=sidebar_items_for(current_user),
        student_profile=student,
        attendance_summary=attendance_summary,
    )


@eleve_bp.route("/notes")
@require_permission(constants.DASHBOARD_ELEVE)
def notes():
    student = scoped_own_student_profile(current_user)
    if not student:
        abort(403)

    enrollment = Enrollment.query.filter_by(student_profile_id=student.id, status=Enrollment.STATUS_ACTIF).first()
    if not enrollment:
        return render_template(
            "dashboard/eleve/notes.html",
            sidebar_items=sidebar_items_for(current_user),
            student=student,
            subject_averages=[],
            overall_average=None,
            selected_term=constants.TERM_T1,
            report_card=None,
        )

    selected_term = request.args.get("term") or constants.TERM_T1
    if selected_term not in constants.TERMS:
        abort(400)

    subject_averages = student_subject_averages(student.id, enrollment.school_year_id, selected_term)
    overall = student_overall_average(student.id, enrollment.school_year_id, selected_term)
    report_card = ReportCard.query.filter_by(
        student_profile_id=student.id, school_year_id=enrollment.school_year_id, term=selected_term
    ).first()

    return render_template(
        "dashboard/eleve/notes.html",
        sidebar_items=sidebar_items_for(current_user),
        student=student,
        subject_averages=subject_averages,
        overall_average=overall,
        selected_term=selected_term,
        report_card=report_card,
    )


@eleve_bp.route("/bulletins/<int:report_card_id>.pdf")
@require_permission(constants.DASHBOARD_ELEVE)
def bulletin_download(report_card_id):
    student = scoped_own_student_profile(current_user)
    report_card = ReportCard.query.get_or_404(report_card_id)
    if not student or report_card.student_profile_id != student.id:
        abort(403)

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


@eleve_bp.route("/emploi-du-temps")
@require_permission(constants.DASHBOARD_ELEVE)
def schedule():
    student = scoped_own_student_profile(current_user)
    entries = []
    if student:
        enrollment = Enrollment.query.filter_by(student_profile_id=student.id, status=Enrollment.STATUS_ACTIF).first()
        if enrollment:
            entries = Schedule.query.filter_by(
                classe_id=enrollment.classe_id, school_year_id=enrollment.school_year_id
            ).all()
            entries.sort(key=lambda s: (Schedule.DAY_ORDER[s.day], s.start_time))

    return render_template(
        "dashboard/eleve/schedule.html",
        sidebar_items=sidebar_items_for(current_user),
        entries=entries,
        day_labels=Schedule.DAY_LABELS,
    )


def _own_active_enrollment(student):
    return Enrollment.query.filter_by(student_profile_id=student.id, status=Enrollment.STATUS_ACTIF).first()


@eleve_bp.route("/bibliotheque")
@require_permission(constants.DASHBOARD_ELEVE)
def library():
    student = scoped_own_student_profile(current_user)
    materials, homeworks = [], []
    files_by_material, files_by_homework = {}, {}

    if student:
        enrollment = _own_active_enrollment(student)
        if enrollment:
            materials = (
                CourseMaterial.query.filter_by(
                    classe_id=enrollment.classe_id, school_year_id=enrollment.school_year_id
                )
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
        "dashboard/eleve/library.html",
        sidebar_items=sidebar_items_for(current_user),
        materials=materials,
        homeworks=homeworks,
        files_by_material=files_by_material,
        files_by_homework=files_by_homework,
    )


@eleve_bp.route("/bibliotheque/fichiers/<int:document_id>")
@require_permission(constants.DASHBOARD_ELEVE)
def library_file_download(document_id):
    student = scoped_own_student_profile(current_user)
    if not student:
        abort(403)
    enrollment = _own_active_enrollment(student)
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
