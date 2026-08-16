from app.extensions import db
from app.models.mixins import TimestampMixin


class DisciplinaryIncident(db.Model, TimestampMixin):
    """Un fait rapporté concernant un élève. Les sanctions éventuelles sont des lignes
    séparées (DisciplinaryAction) — un incident peut rester sans suite, ou en cumuler
    plusieurs (avertissement puis sanction si récidive)."""

    __tablename__ = "disciplinary_incidents"

    SEVERITY_LOW = "faible"
    SEVERITY_MEDIUM = "moyenne"
    SEVERITY_HIGH = "grave"
    SEVERITY_CHOICES = (SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH)
    SEVERITY_LABELS = {SEVERITY_LOW: "Faible", SEVERITY_MEDIUM: "Moyenne", SEVERITY_HIGH: "Grave"}

    id = db.Column(db.Integer, primary_key=True)
    school_year_id = db.Column(db.Integer, db.ForeignKey("school_years.id"), nullable=False)
    student_profile_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    reported_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    severity = db.Column(db.String(20), nullable=False, default=SEVERITY_LOW)

    student = db.relationship("StudentProfile")
    reported_by = db.relationship("User")
    actions = db.relationship("DisciplinaryAction", back_populates="incident", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DisciplinaryIncident student={self.student_profile_id} date={self.date}>"


class DisciplinaryAction(db.Model, TimestampMixin):
    __tablename__ = "disciplinary_actions"

    TYPE_AVERTISSEMENT = "avertissement"
    TYPE_SANCTION = "sanction"
    TYPE_EXCLUSION = "exclusion"
    TYPE_CHOICES = (TYPE_AVERTISSEMENT, TYPE_SANCTION, TYPE_EXCLUSION)
    TYPE_LABELS = {
        TYPE_AVERTISSEMENT: "Avertissement",
        TYPE_SANCTION: "Sanction",
        TYPE_EXCLUSION: "Exclusion",
    }

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("disciplinary_incidents.id"), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    decided_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    details = db.Column(db.String(500), nullable=True)

    incident = db.relationship("DisciplinaryIncident", back_populates="actions")
    decided_by = db.relationship("User")

    def __repr__(self):
        return f"<DisciplinaryAction {self.type} incident={self.incident_id}>"


class Convocation(db.Model, TimestampMixin):
    """Convocation d'un parent par le Directeur de Discipline (brief section 12).
    `parent_profile_id` pointe vers un parent réellement lié à l'élève (via ParentStudent) —
    pas de contact libre, pour garantir que la convocation atteint un tuteur légitime."""

    __tablename__ = "convocations"

    STATUS_CREEE = "creee"
    STATUS_ENVOYEE = "envoyee"
    STATUS_VUE = "vue"
    STATUS_CONFIRMEE = "confirmee"
    STATUS_TERMINEE = "terminee"
    STATUS_CHOICES = (STATUS_CREEE, STATUS_ENVOYEE, STATUS_VUE, STATUS_CONFIRMEE, STATUS_TERMINEE)
    STATUS_LABELS = {
        STATUS_CREEE: "Créée",
        STATUS_ENVOYEE: "Envoyée",
        STATUS_VUE: "Vue",
        STATUS_CONFIRMEE: "Confirmée",
        STATUS_TERMINEE: "Terminée",
    }

    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    parent_profile_id = db.Column(db.Integer, db.ForeignKey("parent_profiles.id"), nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    motif = db.Column(db.String(500), nullable=False)
    date = db.Column(db.Date, nullable=False)
    heure = db.Column(db.Time, nullable=False)
    lieu = db.Column(db.String(200), nullable=False)
    commentaire = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_CREEE)

    student = db.relationship("StudentProfile")
    parent = db.relationship("ParentProfile")
    created_by = db.relationship("User")

    def __repr__(self):
        return f"<Convocation student={self.student_profile_id} status={self.status}>"
