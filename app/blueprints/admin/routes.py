from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import constants
from app.blueprints.admin import admin_bp
from app.blueprints.admin.forms import SchoolYearForm, SettingsForm, UserForm
from app.extensions import db
from app.models import AuditLog, Role, School, SchoolYear, User
from app.services.audit import log_action
from app.services.permissions import require_permission, sidebar_items_for
from app.services.uploads import UploadError, validate_and_save_upload


@admin_bp.route("/")
@require_permission(constants.ADMIN_MANAGE_SETTINGS)
def dashboard():
    stats = {
        "utilisateurs": User.query.filter_by(deleted_at=None).count(),
        "roles": Role.query.count(),
    }
    return render_template(
        "dashboard/admin/dashboard.html",
        sidebar_items=sidebar_items_for(current_user),
        stats=stats,
    )


@admin_bp.route("/utilisateurs")
@require_permission(constants.ADMIN_MANAGE_USERS)
def users():
    all_users = User.query.filter_by(deleted_at=None).order_by(User.email).all()
    return render_template(
        "dashboard/admin/users.html",
        sidebar_items=sidebar_items_for(current_user),
        users=all_users,
    )


@admin_bp.route("/utilisateurs/nouveau", methods=["GET", "POST"])
@require_permission(constants.ADMIN_MANAGE_USERS)
def user_new():
    form = UserForm()
    if form.validate_on_submit():
        if not form.password.data:
            flash("Le mot de passe est requis pour créer un compte.", "error")
            return render_template(
                "dashboard/admin/user_form.html",
                sidebar_items=sidebar_items_for(current_user),
                form=form,
                editing=False,
            )
        if User.query.filter_by(email=form.email.data.strip().lower()).first():
            flash("Un compte existe déjà avec cet email.", "error")
            return render_template(
                "dashboard/admin/user_form.html",
                sidebar_items=sidebar_items_for(current_user),
                form=form,
                editing=False,
            )

        user = User(
            school_id=current_user.school_id,
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
            is_active_account=form.is_active_account.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        if form.roles.data:
            user.roles = Role.query.filter(Role.code.in_(form.roles.data)).all()

        db.session.commit()
        log_action("user_created", entity_type="User", entity_id=user.id)
        flash(f"Utilisateur {user.email} créé.", "info")
        return redirect(url_for("admin.users"))

    return render_template(
        "dashboard/admin/user_form.html",
        sidebar_items=sidebar_items_for(current_user),
        form=form,
        editing=False,
    )


@admin_bp.route("/utilisateurs/<int:user_id>/modifier", methods=["GET", "POST"])
@require_permission(constants.ADMIN_MANAGE_USERS)
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    if user.deleted_at is not None:
        abort(404)

    form = UserForm(obj=user)
    if not form.is_submitted():
        form.roles.data = [role.code for role in user.roles]

    if form.validate_on_submit():
        new_email = form.email.data.strip().lower()
        if new_email != user.email and User.query.filter_by(email=new_email).first():
            flash("Un autre compte utilise déjà cet email.", "error")
            return render_template(
                "dashboard/admin/user_form.html",
                sidebar_items=sidebar_items_for(current_user),
                form=form,
                editing=True,
                target_user=user,
            )

        user.email = new_email
        user.phone = form.phone.data.strip() if form.phone.data else None
        user.is_active_account = form.is_active_account.data
        if form.password.data:
            user.set_password(form.password.data)
        user.roles = Role.query.filter(Role.code.in_(form.roles.data)).all() if form.roles.data else []

        db.session.commit()
        log_action("user_updated", entity_type="User", entity_id=user.id)
        flash(f"Utilisateur {user.email} mis à jour.", "info")
        return redirect(url_for("admin.users"))

    return render_template(
        "dashboard/admin/user_form.html",
        sidebar_items=sidebar_items_for(current_user),
        form=form,
        editing=True,
        target_user=user,
    )


@admin_bp.route("/parametres", methods=["GET", "POST"])
@require_permission(constants.ADMIN_MANAGE_SETTINGS)
def settings():
    school = School.query.first()
    form = SettingsForm(obj=school)

    if form.validate_on_submit():
        school.name = form.name.data.strip()
        school.city = form.city.data.strip()
        school.province = form.province.data.strip()
        school.country = form.country.data.strip()
        school.currency_default = form.currency_default.data.strip().upper()
        school.primary_color = form.primary_color.data.strip() if form.primary_color.data else None
        school.secondary_color = form.secondary_color.data.strip() if form.secondary_color.data else None
        school.phone = form.phone.data.strip() if form.phone.data else None
        school.address = form.address.data.strip() if form.address.data else None
        school.opening_hours = form.opening_hours.data.strip() if form.opening_hours.data else None
        school.maps_url = form.maps_url.data.strip() if form.maps_url.data else None

        try:
            if form.logo.data and form.logo.data.filename:
                document = validate_and_save_upload(form.logo.data, "School", school.id, "logo", current_user.id)
                school.logo_path = document.file_path
        except UploadError as exc:
            db.session.rollback()
            flash(str(exc), "error")
            return redirect(url_for("admin.settings"))

        db.session.commit()
        log_action("school_settings_updated", entity_type="School", entity_id=school.id)
        flash("Paramètres mis à jour.", "info")
        return redirect(url_for("admin.settings"))

    school_years = SchoolYear.query.filter_by(school_id=current_user.school_id).order_by(
        SchoolYear.start_date.desc()
    ).all()
    year_form = SchoolYearForm()

    return render_template(
        "dashboard/admin/settings.html",
        sidebar_items=sidebar_items_for(current_user),
        school=school,
        form=form,
        school_years=school_years,
        year_form=year_form,
    )


@admin_bp.route("/annees-scolaires/nouvelle", methods=["POST"])
@require_permission(constants.ADMIN_MANAGE_SETTINGS)
def school_year_new():
    form = SchoolYearForm()
    if form.validate_on_submit():
        if form.start_date.data >= form.end_date.data:
            flash("La date de fin doit être après la date de début.", "error")
            return redirect(url_for("admin.settings"))

        existing = SchoolYear.query.filter_by(
            school_id=current_user.school_id, label=form.label.data.strip()
        ).first()
        if existing:
            flash("Une année scolaire avec ce libellé existe déjà.", "error")
            return redirect(url_for("admin.settings"))

        school_year = SchoolYear(
            school_id=current_user.school_id,
            label=form.label.data.strip(),
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            is_current=False,
        )
        db.session.add(school_year)
        db.session.commit()
        log_action("school_year_created", entity_type="SchoolYear", entity_id=school_year.id)
        flash(f"Année scolaire {school_year.label} créée.", "info")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "error")

    return redirect(url_for("admin.settings"))


@admin_bp.route("/annees-scolaires/<int:school_year_id>/activer", methods=["POST"])
@require_permission(constants.ADMIN_MANAGE_SETTINGS)
def school_year_set_current(school_year_id):
    school_year = SchoolYear.query.get_or_404(school_year_id)
    if school_year.school_id != current_user.school_id:
        abort(404)

    SchoolYear.query.filter_by(school_id=current_user.school_id, is_current=True).update({"is_current": False})
    school_year.is_current = True
    db.session.commit()
    log_action("school_year_activated", entity_type="SchoolYear", entity_id=school_year.id)
    flash(f"Année scolaire {school_year.label} définie comme année en cours.", "info")
    return redirect(url_for("admin.settings"))


@admin_bp.route("/journal")
@require_permission(constants.ADMIN_VIEW_AUDIT_LOG)
def audit_log():
    query = AuditLog.query.order_by(AuditLog.created_at.desc())

    action_filter = request.args.get("action", "").strip()
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    user_id_filter = request.args.get("user_id", type=int)
    if user_id_filter:
        query = query.filter(AuditLog.user_id == user_id_filter)

    page = request.args.get("page", type=int, default=1)
    pagination = db.paginate(query, page=page, per_page=50, error_out=False)

    distinct_actions = [row[0] for row in db.session.query(AuditLog.action).distinct().order_by(AuditLog.action).all()]
    users_with_entries = User.query.filter(
        User.id.in_(db.session.query(AuditLog.user_id).distinct())
    ).order_by(User.email).all()

    return render_template(
        "dashboard/admin/audit_log.html",
        sidebar_items=sidebar_items_for(current_user),
        pagination=pagination,
        entries=pagination.items,
        distinct_actions=distinct_actions,
        users_with_entries=users_with_entries,
        selected_action=action_filter,
        selected_user_id=user_id_filter,
    )
