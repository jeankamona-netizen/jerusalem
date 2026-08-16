from flask import Blueprint

direction_etudes_bp = Blueprint("direction_etudes", __name__, url_prefix="/direction-etudes")

from app.blueprints.direction_etudes import routes  # noqa: E402,F401
