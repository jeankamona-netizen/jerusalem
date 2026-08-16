from flask import Flask, render_template

from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    _register_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_template_globals(app)

    return app


def _register_extensions(app):
    from app.extensions import csrf, db, limiter, login_manager, migrate

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "info"
    csrf.init_app(app)
    limiter.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))


def _register_blueprints(app):
    from app.blueprints.admin import admin_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.comptable import comptable_bp
    from app.blueprints.direction_etudes import direction_etudes_bp
    from app.blueprints.discipline import discipline_bp
    from app.blueprints.eleve import eleve_bp
    from app.blueprints.enseignant import enseignant_bp
    from app.blueprints.notifications import notifications_bp
    from app.blueprints.parent import parent_bp
    from app.blueprints.prefet import prefet_bp
    from app.blueprints.public import public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(prefet_bp)
    app.register_blueprint(direction_etudes_bp)
    app.register_blueprint(discipline_bp)
    app.register_blueprint(enseignant_bp)
    app.register_blueprint(comptable_bp)
    app.register_blueprint(parent_bp)
    app.register_blueprint(eleve_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notifications_bp)


def _register_template_globals(app):
    from flask_login import current_user

    from app import constants
    from app.models import Notification, School

    @app.context_processor
    def inject_constants():
        return {"constants": constants}

    @app.context_processor
    def inject_school():
        # Une seule ligne School aujourd'hui (voir app/models/core.py) ; School.query.first()
        # est le même raccourci déjà utilisé partout ailleurs dans l'application (préinscription,
        # séquence des reçus, etc.) tant qu'un vrai multi-établissement n'est pas branché.
        return {"school": School.query.first()}

    @app.context_processor
    def inject_unread_notifications_count():
        # Les templates PDF (reçus, bulletins, emplois du temps) sont rendus via
        # render_template() en dehors d'une vraie requête (ex: seed_demo.py, qui n'a
        # qu'un app_context) — current_user y vaut None plutôt que de lever une erreur
        # (comportement de Flask-Login hors contexte de requête), d'où ce garde-fou.
        if not current_user or not current_user.is_authenticated:
            return {"unread_notifications_count": 0}
        count = Notification.query.filter_by(user_id=current_user.id, read_at=None).count()
        return {"unread_notifications_count": count}


def _register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404
