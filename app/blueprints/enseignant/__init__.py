from flask import Blueprint

enseignant_bp = Blueprint("enseignant", __name__, url_prefix="/enseignant")

from app.blueprints.enseignant import routes  # noqa: E402,F401
