from app.extensions import db
from app.models.mixins import TimestampMixin


class Document(db.Model, TimestampMixin):
    """Fichier uploadé, rattaché à une entité quelconque via (owner_type, owner_id) plutôt
    qu'une FK dédiée par type de propriétaire — évite une table Document par module. Validé
    à l'upload (type MIME + taille, voir app/services/uploads.py) avant d'être écrit ici."""

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    owner_type = db.Column(db.String(50), nullable=False)  # "Application", ...
    owner_id = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # "photo", "document_scolaire", ...
    file_path = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    def __repr__(self):
        return f"<Document {self.owner_type}:{self.owner_id} {self.category}>"


class Application(db.Model, TimestampMixin):
    """Dossier de préinscription publique (brief section 6). Le numéro de dossier suit le
    même format que les reçus (CSJ-<année>-XXXXX, voir app/services/pdf.next_document_number),
    réutilisé ici via son propre compteur puisque `number` est générique sur le modèle."""

    __tablename__ = "applications"

    STATUS_SOUMIS = "soumis"
    STATUS_EN_EXAMEN = "en_examen"
    STATUS_INCOMPLET = "incomplet"
    STATUS_ACCEPTE = "accepte"
    STATUS_REFUSE = "refuse"
    STATUS_CHOICES = (STATUS_SOUMIS, STATUS_EN_EXAMEN, STATUS_INCOMPLET, STATUS_ACCEPTE, STATUS_REFUSE)
    STATUS_LABELS = {
        STATUS_SOUMIS: "Soumis",
        STATUS_EN_EXAMEN: "En examen",
        STATUS_INCOMPLET: "Incomplet",
        STATUS_ACCEPTE: "Accepté",
        STATUS_REFUSE: "Refusé",
    }

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    number = db.Column(db.String(30), unique=True, nullable=False)

    # Élève
    nom = db.Column(db.String(120), nullable=False)
    postnom = db.Column(db.String(120), nullable=True)
    prenom = db.Column(db.String(120), nullable=True)
    sexe = db.Column(db.String(1), nullable=True)
    date_naissance = db.Column(db.Date, nullable=True)
    lieu_naissance = db.Column(db.String(150), nullable=True)
    nationalite = db.Column(db.String(80), nullable=True, default="Congolaise")
    adresse = db.Column(db.String(300), nullable=True)
    ancienne_ecole = db.Column(db.String(200), nullable=True)
    classe_demandee_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True)

    # Parent / tuteur
    parent_nom = db.Column(db.String(120), nullable=False)
    parent_telephone = db.Column(db.String(30), nullable=False)
    parent_email = db.Column(db.String(255), nullable=True)
    parent_adresse = db.Column(db.String(300), nullable=True)
    parent_relation = db.Column(db.String(50), nullable=False, default="Parent")

    status = db.Column(db.String(20), nullable=False, default=STATUS_SOUMIS)
    decision_comment = db.Column(db.String(500), nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    decided_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    resulting_student_profile_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=True)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)

    classe_demandee = db.relationship("Classe")
    decided_by = db.relationship("User")
    resulting_student = db.relationship("StudentProfile")

    @property
    def full_name(self):
        return " ".join(p for p in [self.nom, self.postnom, self.prenom] if p)

    def __repr__(self):
        return f"<Application {self.number} {self.status}>"
