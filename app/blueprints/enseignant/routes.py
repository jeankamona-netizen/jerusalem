import datetime
import os
from decimal import Decimal, InvalidOperation

from flask import abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from app import constants
from app.blueprints.enseignant import enseignant_bp
from app.blueprints.enseignant.forms import AssessmentForm, AttendanceSessionForm, CourseMaterialForm, HomeworkForm
from app.extensions import db
from app.models import (
    Assessment,
    AssessmentType,
    Attendance,
    Classe,
    CourseMaterial,
    Document,
    Enrollment,
    Grade,
    Homework,
    Notification,
    Schedule,
)
from app.models.mixins import utcnow
from app.services.audit import log_action
from app.services.notifications import notify
from app.services.permissions import require_permission, sidebar_items_for
from app.services.schedule import teacher_affectations
from app.services.school_year import get_current_school_year
from app.services.uploads import UploadError, validate_and_save_upload


@enseignant_bp.route("/")
@require_permission(constants.DASHBOARD_ENSEIGNANT)
def dashboard():
    stats = {"cours_aujourd_hui": 0, "mes_classes": 0}
    if current_user.teacher_profile:
        school_year = get_current_school_year(current_user.school_id)
        if school_year:
            affectations = teacher_affectations(current_user.teacher_profile.id, school_year.id)
            stats["mes_classes"] = len({classe.id for classe, _subject in affectations})

            weekday = datetime.date.today().weekday()
            if weekday < len(Schedule.DAY_CHOICES):
                today_code = Schedule.DAY_CHOICES[weekday]
                stats["cours_aujourd_hui"] = Schedule.query.filter_by(
                    teacher_profile_id=current_user.teacher_profile.id,
                    school_year_id=school_year.id,
                    day=today_code,
                ).count()

    return render_template(
        "dashboard/enseignant/dashboard.html",
        sidebar_items=sidebar_items_for(current_user),
        teacher_profile=current_user.teacher_profile,
        stats=stats,
    )


def _own_assessments_query():
    return Assessment.query.filter_by(teacher_profile_id=current_user.teacher_profile.id).order_by(
        Assessment.date.desc()
    )


@enseignant_bp.route("/evaluations", methods=["GET", "POST"])
@require_permission(constants.GRADES_MANAGE_OWN)
def assessments():
    if not current_user.teacher_profile:
        abort(403)

    school_year = get_current_school_year(current_user.school_id)
    affectations = teacher_affectations(current_user.teacher_profile.id, school_year.id) if school_year else []

    form = None
    if affectations:
        form = AssessmentForm()
        form.classe_subject.choices = [
            (f"{classe.id}:{subject.id}", f"{classe.name} — {subject.name}") for classe, subject in affectations
        ]
        form.assessment_type_id.choices = [
            (t.id, t.label) for t in AssessmentType.query.order_by(AssessmentType.label).all()
        ]

        if form.validate_on_submit():
            classe_id_str, subject_id_str = form.classe_subject.data.split(":")
            classe = Classe.query.get_or_404(int(classe_id_str))
            assessment = Assessment(
                subject_id=int(subject_id_str),
                classe_id=classe.id,
                teacher_profile_id=current_user.teacher_profile.id,
                assessment_type_id=form.assessment_type_id.data,
                school_year_id=classe.school_year_id,
                term=form.term.data,
                date=form.date.data,
                coefficient=form.coefficient.data,
                max_score=form.max_score.data,
            )
            db.session.add(assessment)
            db.session.commit()
            log_action("assessment_created", entity_type="Assessment", entity_id=assessment.id)
            flash("Évaluation créée. Vous pouvez maintenant encoder les notes.", "info")
            return redirect(url_for("enseignant.assessment_grades", assessment_id=assessment.id))

    return render_template(
        "dashboard/enseignant/assessments.html",
        sidebar_items=sidebar_items_for(current_user),
        form=form,
        assessments=_own_assessments_query().all(),
    )


@enseignant_bp.route("/evaluations/<int:assessment_id>/notes", methods=["GET", "POST"])
@require_permission(constants.GRADES_MANAGE_OWN)
def assessment_grades(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    if assessment.teacher_profile_id != current_user.teacher_profile.id:
        abort(403)

    enrollments = Enrollment.query.filter_by(
        classe_id=assessment.classe_id,
        school_year_id=assessment.school_year_id,
        status=Enrollment.STATUS_ACTIF,
    ).all()
    students = sorted((e.student for e in enrollments), key=lambda s: s.nom)

    existing_grades = {g.student_profile_id: g for g in Grade.query.filter_by(assessment_id=assessment.id).all()}

    if request.method == "POST":
        for student in students:
            raw_score = request.form.get(f"score_{student.id}", "").strip()
            grade = existing_grades.get(student.id)

            if raw_score == "":
                score = None
            else:
                try:
                    score = Decimal(raw_score)
                except InvalidOperation:
                    flash(f"Note invalide pour {student.full_name}, ignorée.", "error")
                    continue
                if score < 0 or score > assessment.max_score:
                    flash(f"Note hors barème pour {student.full_name} (0 à {assessment.max_score}), ignorée.", "error")
                    continue

            if grade:
                grade.score = score
                grade.entered_by_user_id = current_user.id
                grade.entered_at = utcnow()
            else:
                db.session.add(
                    Grade(
                        assessment_id=assessment.id,
                        student_profile_id=student.id,
                        score=score,
                        entered_by_user_id=current_user.id,
                        entered_at=utcnow(),
                    )
                )

        db.session.commit()
        log_action("grades_saved", entity_type="Assessment", entity_id=assessment.id)
        flash("Notes enregistrées.", "info")
        existing_grades = {g.student_profile_id: g for g in Grade.query.filter_by(assessment_id=assessment.id).all()}

    return render_template(
        "dashboard/enseignant/assessment_grades.html",
        sidebar_items=sidebar_items_for(current_user),
        assessment=assessment,
        students=students,
        existing_grades=existing_grades,
    )


@enseignant_bp.route("/presence", methods=["GET", "POST"])
@require_permission(constants.ATTENDANCE_RECORD)
def attendance_form():
    if not current_user.teacher_profile:
        abort(403)

    school_year = get_current_school_year(current_user.school_id)
    affectations = teacher_affectations(current_user.teacher_profile.id, school_year.id) if school_year else []
    affected_classes = sorted({classe for classe, _ in affectations}, key=lambda c: c.name)
    affected_subjects = sorted({subject for _, subject in affectations}, key=lambda s: s.name)

    session_form = AttendanceSessionForm()
    session_form.classe_id.choices = [(c.id, c.name) for c in affected_classes]
    session_form.subject_id.choices = [("", "— Appel général —")] + [
        (str(s.id), s.name) for s in affected_subjects
    ]

    if not affected_classes:
        return render_template(
            "dashboard/enseignant/attendance_form.html",
            sidebar_items=sidebar_items_for(current_user),
            form=session_form,
            students=None,
            existing={},
            classe=None,
            date=None,
            subject_id_raw="",
            attendance_status=Attendance,
        )

    classe_id = request.values.get("classe_id", type=int)
    subject_id_raw = request.values.get("subject_id", "")
    date_raw = request.values.get("date")

    students = None
    existing = {}
    classe = None
    date = None

    if classe_id and date_raw:
        if classe_id not in {c.id for c in affected_classes}:
            abort(403)
        classe = Classe.query.get_or_404(classe_id)
        subject_id = int(subject_id_raw) if subject_id_raw else None
        try:
            date = datetime.date.fromisoformat(date_raw)
        except ValueError:
            abort(400)

        enrollments = Enrollment.query.filter_by(
            classe_id=classe.id, school_year_id=classe.school_year_id, status=Enrollment.STATUS_ACTIF
        ).all()
        students = sorted((e.student for e in enrollments), key=lambda s: s.nom)
        existing = {
            a.student_profile_id: a
            for a in Attendance.query.filter_by(classe_id=classe.id, subject_id=subject_id, date=date).all()
        }

        if request.method == "POST":
            for student in students:
                status = request.form.get(f"status_{student.id}", Attendance.STATUS_PRESENT)
                if status not in Attendance.STATUS_CHOICES:
                    continue
                arrival_raw = request.form.get(f"arrival_{student.id}", "").strip()
                comment = request.form.get(f"comment_{student.id}", "").strip() or None
                arrival_time = None
                if arrival_raw:
                    try:
                        arrival_time = datetime.time.fromisoformat(arrival_raw)
                    except ValueError:
                        arrival_time = None

                record = existing.get(student.id)
                previous_status = record.status if record else None
                if record:
                    record.status = status
                    record.arrival_time = arrival_time
                    record.comment = comment
                    record.recorded_by_user_id = current_user.id
                else:
                    db.session.add(
                        Attendance(
                            student_profile_id=student.id,
                            classe_id=classe.id,
                            subject_id=subject_id,
                            school_year_id=classe.school_year_id,
                            date=date,
                            status=status,
                            arrival_time=arrival_time,
                            comment=comment,
                            recorded_by_user_id=current_user.id,
                        )
                    )

                # On ne notifie que la transition vers absent/retard (pas à chaque
                # réenregistrement du même statut) pour ne pas spammer le parent.
                if status in (Attendance.STATUS_ABSENT, Attendance.STATUS_RETARD) and status != previous_status:
                    notif_type = (
                        Notification.TYPE_ABSENCE if status == Attendance.STATUS_ABSENT else Notification.TYPE_RETARD
                    )
                    label = "absent(e)" if status == Attendance.STATUS_ABSENT else "en retard"
                    for parent in student.parents:
                        notify(
                            parent.user,
                            notif_type,
                            title=f"{student.full_name} — {label}",
                            body=f"Signalé {label} le {date.strftime('%d/%m/%Y')} ({classe.name}).",
                        )

            db.session.commit()
            log_action("attendance_recorded", entity_type="Classe", entity_id=classe.id)
            flash("Présences enregistrées.", "info")
            existing = {
                a.student_profile_id: a
                for a in Attendance.query.filter_by(classe_id=classe.id, subject_id=subject_id, date=date).all()
            }

        session_form.classe_id.data = classe.id
        session_form.subject_id.data = subject_id_raw
        session_form.date.data = date

    return render_template(
        "dashboard/enseignant/attendance_form.html",
        sidebar_items=sidebar_items_for(current_user),
        form=session_form,
        students=students,
        existing=existing,
        classe=classe,
        date=date,
        subject_id_raw=subject_id_raw,
        attendance_status=Attendance,
    )


@enseignant_bp.route("/emploi-du-temps")
@require_permission(constants.DASHBOARD_ENSEIGNANT)
def my_schedule():
    if not current_user.teacher_profile:
        abort(403)

    school_year = get_current_school_year(current_user.school_id)
    entries = []
    if school_year:
        entries = Schedule.query.filter_by(
            teacher_profile_id=current_user.teacher_profile.id, school_year_id=school_year.id
        ).all()
        entries.sort(key=lambda s: (Schedule.DAY_ORDER[s.day], s.start_time))

    return render_template(
        "dashboard/enseignant/schedule.html",
        sidebar_items=sidebar_items_for(current_user),
        entries=entries,
        day_labels=Schedule.DAY_LABELS,
    )


@enseignant_bp.route("/bibliotheque", methods=["GET", "POST"])
@require_permission(constants.LIBRARY_MANAGE_OWN)
def library():
    if not current_user.teacher_profile:
        abort(403)

    school_year = get_current_school_year(current_user.school_id)
    affectations = teacher_affectations(current_user.teacher_profile.id, school_year.id) if school_year else []

    material_form = None
    homework_form = None
    if affectations:
        choices = [(f"{classe.id}:{subject.id}", f"{classe.name} — {subject.name}") for classe, subject in affectations]
        material_form = CourseMaterialForm()
        material_form.classe_subject.choices = choices
        homework_form = HomeworkForm()
        homework_form.classe_subject.choices = choices

        if request.form.get("form_name") == "material" and material_form.validate_on_submit():
            classe_id_str, subject_id_str = material_form.classe_subject.data.split(":")
            material = CourseMaterial(
                school_year_id=school_year.id,
                classe_id=int(classe_id_str),
                subject_id=int(subject_id_str),
                teacher_profile_id=current_user.teacher_profile.id,
                title=material_form.title.data.strip(),
                description=material_form.description.data.strip() if material_form.description.data else None,
                category=material_form.category.data,
            )
            db.session.add(material)
            db.session.flush()
            try:
                if material_form.file.data and material_form.file.data.filename:
                    validate_and_save_upload(
                        material_form.file.data, "CourseMaterial", material.id, "file", current_user.id
                    )
            except UploadError as exc:
                db.session.rollback()
                flash(str(exc), "error")
                return redirect(url_for("enseignant.library"))
            db.session.commit()
            log_action("course_material_created", entity_type="CourseMaterial", entity_id=material.id)
            flash("Support de cours ajouté.", "info")
            return redirect(url_for("enseignant.library"))

        if request.form.get("form_name") == "homework" and homework_form.validate_on_submit():
            classe_id_str, subject_id_str = homework_form.classe_subject.data.split(":")
            homework = Homework(
                school_year_id=school_year.id,
                classe_id=int(classe_id_str),
                subject_id=int(subject_id_str),
                teacher_profile_id=current_user.teacher_profile.id,
                title=homework_form.title.data.strip(),
                instructions=homework_form.instructions.data.strip() if homework_form.instructions.data else None,
                due_date=homework_form.due_date.data,
            )
            db.session.add(homework)
            db.session.flush()
            try:
                if homework_form.file.data and homework_form.file.data.filename:
                    validate_and_save_upload(homework_form.file.data, "Homework", homework.id, "file", current_user.id)
            except UploadError as exc:
                db.session.rollback()
                flash(str(exc), "error")
                return redirect(url_for("enseignant.library"))
            db.session.commit()
            log_action("homework_created", entity_type="Homework", entity_id=homework.id)
            flash("Devoir ajouté.", "info")
            return redirect(url_for("enseignant.library"))

    materials = (
        CourseMaterial.query.filter_by(teacher_profile_id=current_user.teacher_profile.id)
        .order_by(CourseMaterial.created_at.desc())
        .all()
    )
    homeworks = (
        Homework.query.filter_by(teacher_profile_id=current_user.teacher_profile.id)
        .order_by(Homework.due_date.desc())
        .all()
    )
    files_by_material = {
        d.owner_id: d for d in Document.query.filter_by(owner_type="CourseMaterial", category="file").all()
    }
    files_by_homework = {
        d.owner_id: d for d in Document.query.filter_by(owner_type="Homework", category="file").all()
    }

    return render_template(
        "dashboard/enseignant/library.html",
        sidebar_items=sidebar_items_for(current_user),
        material_form=material_form,
        homework_form=homework_form,
        materials=materials,
        homeworks=homeworks,
        files_by_material=files_by_material,
        files_by_homework=files_by_homework,
    )


@enseignant_bp.route("/bibliotheque/supports/<int:material_id>/supprimer", methods=["POST"])
@require_permission(constants.LIBRARY_MANAGE_OWN)
def material_delete(material_id):
    material = CourseMaterial.query.get_or_404(material_id)
    if material.teacher_profile_id != current_user.teacher_profile.id:
        abort(403)
    Document.query.filter_by(owner_type="CourseMaterial", owner_id=material.id).delete()
    db.session.delete(material)
    db.session.commit()
    log_action("course_material_deleted", entity_type="CourseMaterial", entity_id=material_id)
    flash("Support supprimé.", "info")
    return redirect(url_for("enseignant.library"))


@enseignant_bp.route("/bibliotheque/devoirs/<int:homework_id>/supprimer", methods=["POST"])
@require_permission(constants.LIBRARY_MANAGE_OWN)
def homework_delete(homework_id):
    homework = Homework.query.get_or_404(homework_id)
    if homework.teacher_profile_id != current_user.teacher_profile.id:
        abort(403)
    Document.query.filter_by(owner_type="Homework", owner_id=homework.id).delete()
    db.session.delete(homework)
    db.session.commit()
    log_action("homework_deleted", entity_type="Homework", entity_id=homework_id)
    flash("Devoir supprimé.", "info")
    return redirect(url_for("enseignant.library"))


@enseignant_bp.route("/bibliotheque/fichiers/<int:document_id>")
@require_permission(constants.LIBRARY_MANAGE_OWN)
def library_file_download(document_id):
    document = Document.query.get_or_404(document_id)
    if document.owner_type == "CourseMaterial":
        owner = CourseMaterial.query.get_or_404(document.owner_id)
    elif document.owner_type == "Homework":
        owner = Homework.query.get_or_404(document.owner_id)
    else:
        abort(404)
    if owner.teacher_profile_id != current_user.teacher_profile.id:
        abort(403)
    if not os.path.exists(document.file_path):
        abort(404)
    return send_file(document.file_path, mimetype=document.mime_type, download_name=document.original_filename)
