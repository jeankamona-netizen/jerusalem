from flask import Blueprint

comptable_bp = Blueprint("comptable", __name__, url_prefix="/comptable")

from app.blueprints.comptable import routes  # noqa: E402,F401
