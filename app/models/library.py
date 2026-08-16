from app.extensions import db
from app.models.mixins import TimestampMixin


class CourseMaterial(db.Model, TimestampMixin):
    """Support de cours déposé par un enseignant pour une classe/matière donnée. Le fichier
    joint (optionnel — un support peut être un simple texte de consigne) réutilise le modèle
    Document générique, comme pour les actualités et événements."""

    __tablename__ = "course_materials"

    CATEGORY_SUPPORT = "support_cours"
    CATEGORY_EXERCICE = "exercice"
    CATEGORY_CORRIGE = "corrige"
    CATEGORY_AUTRE = "autre"
    CATEGORY_CHOICES = (CATEGORY_SUPPORT, CATEGORY_EXERCICE, CATEGORY_CORRIGE, CATEGORY_AUTRE)
    CATEGORY_LABELS = {
        CATEGORY_SUPPORT: "Support de cours",
        CATEGORY_EXERCICE: "Exercice",
        CATEGORY_CORRIGE: "Corrigé",
        CATEGORY_AUTRE: "Autre",
    }

    id = db.Column(db.Integer, primary_key=True)
    school_year_id = db.Column(db.Integer, db.ForeignKey("school_years.id"), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    teacher_profile_id = db.Column(db.Integer, db.ForeignKey("teacher_profiles.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(1000), nullable=True)
    category = db.Column(db.String(20), nullable=False, default=CATEGORY_SUPPORT)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)

    classe = db.relationship("Classe")
    subject = db.relationship("Subject")
    teacher_profile = db.relationship("TeacherProfile")

    def __repr__(self):
        return f"<CourseMaterial {self.title} classe={self.classe_id}>"


class Homework(db.Model, TimestampMixin):
    """Devoir donné par un enseignant à une classe pour une matière, avec date d'échéance.
    Fichier joint optionnel (énoncé), même mécanisme que CourseMaterial."""

    __tablename__ = "homeworks"

    id = db.Column(db.Integer, primary_key=True)
    school_year_id = db.Column(db.Integer, db.ForeignKey("school_years.id"), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    teacher_profile_id = db.Column(db.Integer, db.ForeignKey("teacher_profiles.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    instructions = db.Column(db.String(1000), nullable=True)
    due_date = db.Column(db.Date, nullable=False)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)

    classe = db.relationship("Classe")
    subject = db.relationship("Subject")
    teacher_profile = db.relationship("TeacherProfile")

    def __repr__(self):
        return f"<Homework {self.title} classe={self.classe_id} due={self.due_date}>"
