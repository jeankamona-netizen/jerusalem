from app.extensions import db
from app.models.mixins import TimestampMixin


class Classe(db.Model, TimestampMixin):
    """Une classe pour une année scolaire donnée (ex: "6e Sciences A", 2025-2026)."""

    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    school_year_id = db.Column(db.Integer, db.ForeignKey("school_years.id"), nullable=False)

    name = db.Column(db.String(100), nullable=False)  # "6e Sciences A"
    level = db.Column(db.String(50), nullable=False)  # "6e"
    section = db.Column(db.String(80), nullable=True)  # "Sciences"

    school_year = db.relationship("SchoolYear")
    enrollments = db.relationship("Enrollment", back_populates="classe")

    def __repr__(self):
        return f"<Classe {self.name}>"


class Subject(db.Model, TimestampMixin):
    """Matière enseignable. Le coefficient par défaut est configurable, jamais codé
    en dur ailleurs dans l'application (utilisé plus tard par le module Notes)."""

    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    default_coefficient = db.Column(db.Numeric(4, 2), nullable=False, default=1)

    def __repr__(self):
        return f"<Subject {self.name}>"


class Enrollment(db.Model, TimestampMixin):
    """Inscription d'un élève dans une classe pour une année scolaire donnée.
    C'est cette table (et non un simple champ classe_id sur l'élève) qui permet la
    promotion d'une année sur l'autre sans jamais supprimer l'historique (brief section 27)."""

    __tablename__ = "enrollments"
    __table_args__ = (
        db.UniqueConstraint("student_profile_id", "school_year_id", name="uq_enrollment_student_year"),
    )

    STATUS_ACTIF = "actif"
    STATUS_REDOUBLANT = "redoublant"
    STATUS_TRANSFERE = "transfere"
    STATUS_CHOICES = (STATUS_ACTIF, STATUS_REDOUBLANT, STATUS_TRANSFERE)

    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    school_year_id = db.Column(db.Integer, db.ForeignKey("school_years.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_ACTIF)

    student = db.relationship("StudentProfile", back_populates="enrollments")
    classe = db.relationship("Classe", back_populates="enrollments")
    school_year = db.relationship("SchoolYear")

    def __repr__(self):
        return f"<Enrollment student={self.student_profile_id} classe={self.classe_id}>"
