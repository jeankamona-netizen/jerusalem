from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin, utcnow


class School(db.Model, TimestampMixin):
    """Établissement. Une seule ligne aujourd'hui (CS Jérusalem Lubumbashi) ; le modèle
    est prêt pour accueillir d'autres établissements (Kolwezi, Likasi, ...) sans migration
    lourde puisque toutes les tables métier portent déjà school_id."""

    __tablename__ = "schools"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(120), nullable=False, default="Lubumbashi")
    province = db.Column(db.String(120), nullable=False, default="Haut-Katanga")
    country = db.Column(db.String(120), nullable=False, default="RDC")
    currency_default = db.Column(db.String(10), nullable=False, default="CDF")
    logo_path = db.Column(db.String(500), nullable=True)
    primary_color = db.Column(db.String(20), nullable=True, default="#1f7a3d")
    secondary_color = db.Column(db.String(20), nullable=True, default="#d62e1f")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Coordonnées publiques (site public : section "Nous contacter" / "Notre localisation").
    phone = db.Column(db.String(30), nullable=True)
    address = db.Column(db.String(300), nullable=True)
    opening_hours = db.Column(db.String(200), nullable=True)
    maps_url = db.Column(db.String(500), nullable=True)

    school_years = db.relationship("SchoolYear", back_populates="school")
    users = db.relationship("User", back_populates="school")

    def __repr__(self):
        return f"<School {self.name}>"


class SchoolYear(db.Model, TimestampMixin):
    """Une année scolaire (ex: 2025-2026). Les données pédagogiques/financières portent
    school_year_id pour ne jamais mélanger deux années (voir brief section 26)."""

    __tablename__ = "school_years"
    __table_args__ = (db.UniqueConstraint("school_id", "label", name="uq_school_year_label"),)

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    label = db.Column(db.String(20), nullable=False)  # "2025-2026"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, nullable=False, default=False)

    school = db.relationship("School", back_populates="school_years")

    def __repr__(self):
        return f"<SchoolYear {self.label}>"


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    label = db.Column(db.String(120), nullable=False)

    permissions = db.relationship("Permission", secondary="role_permissions", back_populates="roles")

    def __repr__(self):
        return f"<Role {self.code}>"


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), unique=True, nullable=False)
    label = db.Column(db.String(200), nullable=False)

    roles = db.relationship("Role", secondary="role_permissions", back_populates="permissions")

    def __repr__(self):
        return f"<Permission {self.code}>"


class RolePermission(db.Model):
    __tablename__ = "role_permissions"

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey("permissions.id"), primary_key=True)


class UserRole(db.Model):
    """Un utilisateur peut avoir plusieurs rôles (ex: enseignant également parent)."""

    __tablename__ = "user_roles"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), primary_key=True)


class User(db.Model, UserMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active_account = db.Column(db.Boolean, nullable=False, default=True)
    must_change_password = db.Column(db.Boolean, nullable=False, default=False)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

    school = db.relationship("School", back_populates="users")
    roles = db.relationship("Role", secondary="user_roles", backref="users")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def has_role(self, role_code):
        return any(r.code == role_code for r in self.roles)

    def has_permission(self, permission_code):
        for role in self.roles:
            for permission in role.permissions:
                if permission.code == permission_code:
                    return True
        return False

    def record_login_success(self):
        self.last_login_at = utcnow()
        self.failed_login_count = 0
        self.locked_until = None

    # Flask-Login utilise get_id() -> str(id) par défaut via UserMixin ; on force is_active
    # ici pour que les comptes désactivés ne puissent pas se connecter.
    @property
    def is_active(self):
        return self.is_active_account and not self.is_deleted

    def __repr__(self):
        return f"<User {self.email}>"
