from flask import Blueprint

parent_bp = Blueprint("parent", __name__, url_prefix="/parent")

from app.blueprints.parent import routes  # noqa: E402,F401
