from datetime import timedelta

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import constants
from app.blueprints.auth import auth_bp
from app.blueprints.auth.forms import LoginForm
from app.extensions import db, limiter
from app.models import User
from app.models.mixins import utcnow
from app.services.audit import log_action

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


def _dashboard_redirect_target():
    for role in current_user.roles:
        endpoint = constants.ROLE_DASHBOARD_ENDPOINT.get(role.code)
        if endpoint:
            return url_for(endpoint)
    return url_for("public.home")


@auth_bp.route("/connexion", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(_dashboard_redirect_target())

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()

        if user and user.locked_until and user.locked_until > utcnow():
            flash("Compte temporairement bloqué suite à plusieurs échecs de connexion. Réessayez plus tard.", "error")
            return render_template("auth/login.html", form=form)

        if user and user.check_password(form.password.data) and user.is_active:
            user.record_login_success()
            db.session.commit()
            login_user(user, remember=form.remember_me.data)
            log_action("login_success", entity_type="User", entity_id=user.id)
            return redirect(request.args.get("next") or _dashboard_redirect_target())

        if user:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
                user.locked_until = utcnow() + LOCKOUT_DURATION
            db.session.commit()
            log_action("login_failed", entity_type="User", entity_id=user.id)
        else:
            log_action("login_failed_unknown_email")

        flash("Identifiants incorrects.", "error")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/deconnexion", methods=["POST"])
@login_required
def logout():
    log_action("logout", entity_type="User", entity_id=current_user.id)
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("public.home"))
