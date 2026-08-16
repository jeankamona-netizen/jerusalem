from app.extensions import db
from app.models.mixins import TimestampMixin


class AssessmentType(db.Model, TimestampMixin):
    """Type d'évaluation configurable (devoir, interrogation, examen, TP...) — jamais
    codé en dur, ajouté ici pour que l'établissement garde la main sur sa nomenclature."""

    __tablename__ = "assessment_types"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    label = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<AssessmentType {self.label}>"


class Assessment(db.Model, TimestampMixin):
    """Une évaluation donnée par un enseignant, pour une classe/matière/trimestre.
    `teacher_profile_id` identifie l'auteur ; le scoping "mes évaluations" d'un enseignant
    est en réalité restreint aux combinaisons classe/matière réellement affectées dans
    l'emploi du temps (voir app.services.schedule.teacher_affectations), pas seulement à
    ce champ — un enseignant ne peut pas créer d'évaluation hors de ses créneaux affectés."""

    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    teacher_profile_id = db.Column(db.Integer, db.ForeignKey("teacher_profiles.id"), nullable=False)
    assessment_type_id = db.Column(db.Integer, db.ForeignKey("assessment_types.id"), nullable=False)
    school_year_id = db.Column(db.Integer, db.ForeignKey("school_years.id"), nullable=False)
    term = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)
    coefficient = db.Column(db.Numeric(4, 2), nullable=False, default=1)
    max_score = db.Column(db.Numeric(5, 2), nullable=False, default=20)

    subject = db.relationship("Subject")
    classe = db.relationship("Classe")
    teacher = db.relationship("TeacherProfile")
    assessment_type = db.relationship("AssessmentType")
    grades = db.relationship("Grade", back_populates="assessment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Assessment {self.subject_id} {self.classe_id} {self.date}>"


class Grade(db.Model, TimestampMixin):
    __tablename__ = "grades"
    __table_args__ = (db.UniqueConstraint("assessment_id", "student_profile_id", name="uq_grade_assessment_student"),)

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=False)
    student_profile_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    score = db.Column(db.Numeric(5, 2), nullable=True)
    comment = db.Column(db.String(300), nullable=True)
    entered_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    entered_at = db.Column(db.DateTime, nullable=True)

    assessment = db.relationship("Assessment", back_populates="grades")
    student = db.relationship("StudentProfile")

    def __repr__(self):
        return f"<Grade assessment={self.assessment_id} student={self.student_profile_id} score={self.score}>"


class ReportCard(db.Model, TimestampMixin):
    """Bulletin généré (PDF). Le modèle du bulletin vit dans `templates/pdf/bulletin.html` :
    en changer la mise en page ne touche pas ce modèle ni le code Python qui l'appelle."""

    __tablename__ = "report_cards"
    __table_args__ = (
        db.UniqueConstraint("student_profile_id", "school_year_id", "term", name="uq_reportcard_student_year_term"),
    )

    STATUS_GENERATED = "generated"

    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    school_year_id = db.Column(db.Integer, db.ForeignKey("school_years.id"), nullable=False)
    term = db.Column(db.String(20), nullable=False)
    generated_at = db.Column(db.DateTime, nullable=True)
    pdf_path = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_GENERATED)

    student = db.relationship("StudentProfile")
    school_year = db.relationship("SchoolYear")

    def __repr__(self):
        return f"<ReportCard student={self.student_profile_id} term={self.term}>"
