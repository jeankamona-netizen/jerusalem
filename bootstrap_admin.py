"""Initialisation minimale d'une instance de PRODUCTION : établissement, catalogue de
rôles/permissions, et le compte Super Admin réel — rien d'autre.

`seed_demo.py` fait ce même travail mais y ajoute ensuite des dizaines de comptes et
d'élèves de démonstration (`is_demo=True`) et une année scolaire aux dates figées : adapté
pour une démo, jamais pour une instance réelle. Ce script est le sous-ensemble strictement
nécessaire pour pouvoir se connecter la première fois — l'année scolaire réelle et les vrais
comptes (enseignants, comptable...) se créent ensuite via l'interface `/admin`, déjà prévue à
cet effet (voir README, section Déploiement en production).

Usage :
    python bootstrap_admin.py
"""

from app import constants, create_app
from app.extensions import db
from app.models import Permission, Role, RolePermission, School, StaffProfile
from seed_demo import assign_role, create_user, get_or_create


def run():
    app = create_app()
    with app.app_context():
        school, created = get_or_create(
            School,
            name="CS Jérusalem Lubumbashi",
            defaults={
                "city": app.config["SCHOOL_CITY"],
                "province": app.config["SCHOOL_PROVINCE"],
                "country": app.config["SCHOOL_COUNTRY"],
                "currency_default": app.config["SCHOOL_CURRENCY_DEFAULT"],
            },
        )

        roles_by_code = {}
        for code, label in constants.ROLE_LABELS.items():
            role, _ = get_or_create(Role, code=code, defaults={"label": label})
            roles_by_code[code] = role

        permissions_by_code = {}
        for code, label in constants.PERMISSION_LABELS.items():
            permission, _ = get_or_create(Permission, code=code, defaults={"label": label})
            permissions_by_code[code] = permission

        # SUPER_ADMIN reçoit automatiquement toutes les permissions.
        for permission in permissions_by_code.values():
            exists = RolePermission.query.filter_by(
                role_id=roles_by_code[constants.SUPER_ADMIN].id, permission_id=permission.id
            ).first()
            if not exists:
                db.session.add(
                    RolePermission(role_id=roles_by_code[constants.SUPER_ADMIN].id, permission_id=permission.id)
                )

        for role_code, permission_codes in constants.ROLE_DEFAULT_PERMISSIONS.items():
            for permission_code in permission_codes:
                exists = RolePermission.query.filter_by(
                    role_id=roles_by_code[role_code].id,
                    permission_id=permissions_by_code[permission_code].id,
                ).first()
                if not exists:
                    db.session.add(
                        RolePermission(
                            role_id=roles_by_code[role_code].id,
                            permission_id=permissions_by_code[permission_code].id,
                        )
                    )

        db.session.commit()

        admin_user = create_user(app.config["ADMIN_EMAIL"], app.config["ADMIN_MOT_DE_PASSE"], school, is_demo=False)
        assign_role(admin_user, roles_by_code[constants.SUPER_ADMIN])
        get_or_create(
            StaffProfile,
            user_id=admin_user.id,
            defaults={"school_id": school.id, "nom": "Administrateur Système", "fonction": "Super Admin"},
        )
        db.session.commit()

        print("Établissement :", school.name, "(nouveau)" if created else "(déjà existant)")
        print("Rôles et permissions synchronisés.")
        print(f"Compte Super Admin prêt : {app.config['ADMIN_EMAIL']}")
        print(
            "Prochaine étape : se connecter, puis créer l'année scolaire réelle et les vrais "
            "comptes via /admin/parametres et /admin/utilisateurs."
        )


if __name__ == "__main__":
    run()
