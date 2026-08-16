from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class StudentProfile(db.Model, TimestampMixin, SoftDeleteMixin):
    """Champs propres à un élève. user_id est nullable : un dossier élève peut exister
    (issu d'une préinscription acceptée) avant qu'un compte de connexion ne soit créé."""

    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)

    matricule = db.Column(db.String(30), unique=True, nullable=True)
    nom = db.Column(db.String(120), nullable=False)
    postnom = db.Column(db.String(120), nullable=True)
    prenom = db.Column(db.String(120), nullable=True)
    sexe = db.Column(db.String(1), nullable=True)  # M / F
    date_naissance = db.Column(db.Date, nullable=True)
    lieu_naissance = db.Column(db.String(150), nullable=True)
    nationalite = db.Column(db.String(80), nullable=True, default="Congolaise")
    adresse = db.Column(db.String(300), nullable=True)
    ancienne_ecole = db.Column(db.String(200), nullable=True)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship("User", backref=db.backref("student_profile", uselist=False))
    parents = db.relationship(
        "ParentProfile", secondary="parent_students", back_populates="children"
    )
    enrollments = db.relationship("Enrollment", back_populates="student", order_by="Enrollment.school_year_id")

    @property
    def full_name(self):
        return " ".join(p for p in [self.nom, self.postnom, self.prenom] if p)

    def __repr__(self):
        return f"<StudentProfile {self.full_name}>"


class ParentProfile(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "parent_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)

    nom = db.Column(db.String(120), nullable=False)
    telephone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    adresse = db.Column(db.String(300), nullable=True)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship("User", backref=db.backref("parent_profile", uselist=False))
    children = db.relationship(
        "StudentProfile", secondary="parent_students", back_populates="parents"
    )

    def __repr__(self):
        return f"<ParentProfile {self.nom}>"


class ParentStudent(db.Model):
    """Table de jointure : garantit qu'un parent ne voit que ses propres enfants
    (voir app/services/permissions.py pour le scoping appliqué sur cette relation)."""

    __tablename__ = "parent_students"

    parent_profile_id = db.Column(db.Integer, db.ForeignKey("parent_profiles.id"), primary_key=True)
    student_profile_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), primary_key=True)
    relation = db.Column(db.String(50), nullable=False, default="Parent")


class TeacherProfile(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "teacher_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)

    nom = db.Column(db.String(120), nullable=False)
    telephone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    matieres_enseignees = db.Column(db.String(300), nullable=True)  # libellé libre pour P0
    is_demo = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship("User", backref=db.backref("teacher_profile", uselist=False))

    def __repr__(self):
        return f"<TeacherProfile {self.nom}>"


class StaffProfile(db.Model, TimestampMixin, SoftDeleteMixin):
    """Personnel administratif : Préfet, Directeurs, Comptables, Super Admin."""

    __tablename__ = "staff_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)

    nom = db.Column(db.String(120), nullable=False)
    fonction = db.Column(db.String(150), nullable=True)
    telephone = db.Column(db.String(30), nullable=True)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship("User", backref=db.backref("staff_profile", uselist=False))

    def __repr__(self):
        return f"<StaffProfile {self.nom}>"
