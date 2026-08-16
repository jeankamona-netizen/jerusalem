from flask import Blueprint

eleve_bp = Blueprint("eleve", __name__, url_prefix="/eleve")

from app.blueprints.eleve import routes  # noqa: E402,F401
