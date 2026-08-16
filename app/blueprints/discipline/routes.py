import datetime

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import constants
from app.blueprints.discipline import discipline_bp
from app.blueprints.discipline.forms import ActionForm, ConvocationForm, IncidentForm
from app.extensions import db
from app.models import Attendance, Convocation, DisciplinaryAction, DisciplinaryIncident, Notification, StudentProfile
from app.services.attendance import daily_school_stats
from app.services.audit import log_action
from app.services.discipline import student_discipline_summary
from app.services.notifications import notify
from app.services.permissions import require_permission, sidebar_items_for
from app.services.school_year import get_current_school_year


def _active_students_choices(school_id):
    students = (
        StudentProfile.query.filter_by(school_id=school_id, deleted_at=None).order_by(StudentProfile.nom).all()
    )
    return [(s.id, s.full_name) for s in students]


@discipline_bp.route("/")
@require_permission(constants.DASHBOARD_DISCIPLINE)
def dashboard():
    school_year = get_current_school_year(current_user.school_id)
    stats = daily_school_stats(school_year, datetime.date.today()) if school_year else None

    convocations_en_attente = Convocation.query.filter(
        Convocation.status.in_([Convocation.STATUS_CREEE, Convocation.STATUS_ENVOYEE, Convocation.STATUS_VUE])
    ).count()
    incidents_recents = DisciplinaryIncident.query.filter(
        DisciplinaryIncident.date >= datetime.date.today() - datetime.timedelta(days=7)
    ).count()

    return render_template(
        "dashboard/discipline/dashboard.html",
        sidebar_items=sidebar_items_for(current_user),
        stats=stats,
        convocations_en_attente=convocations_en_attente,
        incidents_recents=incidents_recents,
    )


@discipline_bp.route("/presence")
@require_permission(constants.ATTENDANCE_VIEW_ALL)
def attendance_overview():
    school_year = get_current_school_year(current_user.school_id)
    date_raw = request.args.get("date")
    try:
        date = datetime.date.fromisoformat(date_raw) if date_raw else datetime.date.today()
    except ValueError:
        abort(400)

    records = []
    if school_year:
        records = (
            Attendance.query.filter(
                Attendance.school_year_id == school_year.id,
                Attendance.date == date,
                Attendance.status.in_([Attendance.STATUS_ABSENT, Attendance.STATUS_RETARD]),
            )
            .join(Attendance.student)
            .order_by(Attendance.status.desc())
            .all()
        )
        records.sort(key=lambda r: (r.classe.name, r.student.nom))

    return render_template(
        "dashboard/discipline/attendance_overview.html",
        sidebar_items=sidebar_items_for(current_user),
        records=records,
        date=date,
    )


@discipline_bp.route("/presence/<int:attendance_id>/justifier", methods=["POST"])
@require_permission(constants.ATTENDANCE_JUSTIFY)
def justify_attendance(attendance_id):
    record = Attendance.query.get_or_404(attendance_id)
    record.justified = not record.justified
    db.session.commit()
    log_action(
        "attendance_justified" if record.justified else "attendance_unjustified",
        entity_type="Attendance",
        entity_id=record.id,
    )
    flash("Justification mise à jour.", "info")
    return redirect(url_for("discipline.attendance_overview", date=record.date.isoformat()))


@discipline_bp.route("/incidents")
@require_permission(constants.DISCIPLINE_VIEW_ALL)
def incidents():
    can_manage = current_user.has_permission(constants.DISCIPLINE_MANAGE)
    incidents_list = DisciplinaryIncident.query.order_by(DisciplinaryIncident.date.desc()).all()
    return render_template(
        "dashboard/discipline/incidents.html",
        sidebar_items=sidebar_items_for(current_user),
        incidents=incidents_list,
        can_manage=can_manage,
    )


@discipline_bp.route("/incidents/nouveau", methods=["GET", "POST"])
@require_permission(constants.DISCIPLINE_MANAGE)
def incident_new():
    school_year = get_current_school_year(current_user.school_id)
    if not school_year:
        flash("Aucune année scolaire active.", "error")
        return redirect(url_for("discipline.incidents"))

    form = IncidentForm()
    form.student_profile_id.choices = _active_students_choices(current_user.school_id)

    if form.validate_on_submit():
        incident = DisciplinaryIncident(
            school_year_id=school_year.id,
            student_profile_id=form.student_profile_id.data,
            reported_by_user_id=current_user.id,
            date=form.date.data,
            description=form.description.data.strip(),
            severity=form.severity.data,
        )
        db.session.add(incident)
        db.session.commit()
        log_action("incident_created", entity_type="DisciplinaryIncident", entity_id=incident.id)
        flash("Incident enregistré.", "info")
        return redirect(url_for("discipline.incident_detail", incident_id=incident.id))

    return render_template(
        "dashboard/discipline/incident_new.html",
        sidebar_items=sidebar_items_for(current_user),
        form=form,
    )


@discipline_bp.route("/incidents/<int:incident_id>", methods=["GET", "POST"])
@require_permission(constants.DISCIPLINE_VIEW_ALL)
def incident_detail(incident_id):
    incident = DisciplinaryIncident.query.get_or_404(incident_id)
    can_manage = current_user.has_permission(constants.DISCIPLINE_MANAGE)

    form = None
    if can_manage:
        form = ActionForm()
        if not form.is_submitted():
            form.date.data = datetime.date.today()

        if request.method == "POST" and form.validate_on_submit():
            action = DisciplinaryAction(
                incident_id=incident.id,
                type=form.type.data,
                decided_by_user_id=current_user.id,
                date=form.date.data,
                details=form.details.data.strip() if form.details.data else None,
            )
            db.session.add(action)
            db.session.commit()
            log_action("disciplinary_action_added", entity_type="DisciplinaryAction", entity_id=action.id)
            flash("Mesure ajoutée au dossier.", "info")
            return redirect(url_for("discipline.incident_detail", incident_id=incident.id))

    return render_template(
        "dashboard/discipline/incident_detail.html",
        sidebar_items=sidebar_items_for(current_user),
        incident=incident,
        form=form,
        can_manage=can_manage,
    )


@discipline_bp.route("/convocations")
@require_permission(constants.DISCIPLINE_VIEW_ALL)
def convocations():
    convocations_list = Convocation.query.order_by(Convocation.date.desc()).all()
    return render_template(
        "dashboard/discipline/convocations.html",
        sidebar_items=sidebar_items_for(current_user),
        convocations=convocations_list,
        can_manage=current_user.has_permission(constants.DISCIPLINE_MANAGE),
    )


@discipline_bp.route("/convocations/nouvelle", methods=["GET", "POST"])
@require_permission(constants.DISCIPLINE_MANAGE)
def convocation_new():
    student_id = request.values.get("student_id", type=int)
    student = None
    form = None

    if student_id:
        student = StudentProfile.query.get_or_404(student_id)
        parents = list(student.parents)
        if not parents:
            flash(f"Aucun parent/tuteur lié à {student.full_name}. Impossible de créer une convocation.", "error")
            return render_template(
                "dashboard/discipline/convocation_new.html",
                sidebar_items=sidebar_items_for(current_user),
                student=student,
                form=None,
                student_choices=_active_students_choices(current_user.school_id),
            )

        form = ConvocationForm()
        form.parent_profile_id.choices = [(p.id, p.nom) for p in parents]
        if not form.is_submitted():
            form.date.data = datetime.date.today()

        if form.validate_on_submit():
            convocation = Convocation(
                student_profile_id=student.id,
                parent_profile_id=form.parent_profile_id.data,
                created_by_user_id=current_user.id,
                motif=form.motif.data.strip(),
                date=form.date.data,
                heure=form.heure.data,
                lieu=form.lieu.data.strip(),
                commentaire=form.commentaire.data.strip() if form.commentaire.data else None,
                status=Convocation.STATUS_CREEE,
            )
            db.session.add(convocation)
            db.session.commit()
            log_action("convocation_created", entity_type="Convocation", entity_id=convocation.id)
            flash("Convocation créée.", "info")
            return redirect(url_for("discipline.convocations"))

    return render_template(
        "dashboard/discipline/convocation_new.html",
        sidebar_items=sidebar_items_for(current_user),
        student=student,
        form=form,
        student_choices=_active_students_choices(current_user.school_id),
    )


@discipline_bp.route("/convocations/<int:convocation_id>/statut", methods=["POST"])
@require_permission(constants.DISCIPLINE_MANAGE)
def convocation_set_status(convocation_id):
    convocation = Convocation.query.get_or_404(convocation_id)
    new_status = request.form.get("status")
    if new_status not in Convocation.STATUS_CHOICES:
        abort(400)
    convocation.status = new_status
    db.session.commit()
    log_action("convocation_status_changed", entity_type="Convocation", entity_id=convocation.id, new_value=new_status)

    if new_status == Convocation.STATUS_ENVOYEE:
        notify(
            convocation.parent.user,
            Notification.TYPE_CONVOCATION,
            title=f"Convocation — {convocation.student.full_name}",
            body=f"{convocation.motif}, le {convocation.date.strftime('%d/%m/%Y')} à {convocation.heure.strftime('%H:%M')} ({convocation.lieu}).",
            related_url=url_for("parent.child_convocations", student_id=convocation.student_profile_id),
        )
        db.session.commit()

    flash("Statut de la convocation mis à jour.", "info")
    return redirect(url_for("discipline.convocations"))


@discipline_bp.route("/eleves/<int:student_id>")
@require_permission(constants.DISCIPLINE_VIEW_ALL)
def student_file(student_id):
    student = StudentProfile.query.get_or_404(student_id)
    school_year = get_current_school_year(current_user.school_id)
    summary = student_discipline_summary(student.id, school_year.id) if school_year else None

    return render_template(
        "dashboard/discipline/student_file.html",
        sidebar_items=sidebar_items_for(current_user),
        student=student,
        summary=summary,
    )
