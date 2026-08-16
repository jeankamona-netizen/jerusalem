"""RBAC : vérification de permission côté backend (jamais seulement côté template)
et scoping objet (un enseignant/parent/élève ne voit que ce qui lui appartient).

Toute route protégée doit utiliser @require_permission(...) ou @require_role(...) ;
cacher un lien dans la sidebar ne suffit jamais à protéger une route.
"""

from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from app import constants


def require_permission(permission_code):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(*args, **kwargs):
            if not current_user.has_permission(permission_code):
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def require_role(*role_codes):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(*args, **kwargs):
            if not any(current_user.has_role(code) for code in role_codes):
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def sidebar_items_for(user):
    """Sidebar générée à partir des permissions réelles de l'utilisateur, jamais d'un
    `if role == 'ENSEIGNANT'` codé en dur : un Comptable ne voit "Utilisateurs" que s'il a
    effectivement la permission admin.manage_users."""
    if not user or not user.is_authenticated:
        return []
    return [item for item in constants.SIDEBAR_ITEMS if user.has_permission(item["permission"])]


def scoped_children_for(user):
    """Un parent ne voit que les StudentProfile réellement liés via ParentStudent."""
    parent_profile = getattr(user, "parent_profile", None)
    if not parent_profile:
        return []
    return list(parent_profile.children)


def scoped_own_student_profile(user):
    """Un élève ne voit que son propre dossier."""
    return getattr(user, "student_profile", None)
