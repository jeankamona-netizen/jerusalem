from flask import Blueprint

prefet_bp = Blueprint("prefet", __name__, url_prefix="/prefet")

from app.blueprints.prefet import routes  # noqa: E402,F401
