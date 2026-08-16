from app.extensions import db
from app.models.mixins import TimestampMixin


class Notification(db.Model, TimestampMixin):
    """Notification centrale (brief section 25). `channel` enregistre par quel canal elle a
    été envoyée — `web` et `email` sont réellement livrés (voir
    `app/services/notifications.py`) ; `sms`/`whatsapp` restent des stubs en attente du choix
    d'un fournisseur par l'établissement (brief : "ne pas implémenter tous les fournisseurs
    immédiatement")."""

    __tablename__ = "notifications"

    TYPE_ANNONCE = "annonce"
    TYPE_RESULTAT = "resultat"
    TYPE_ABSENCE = "absence"
    TYPE_RETARD = "retard"
    TYPE_CONVOCATION = "convocation"
    TYPE_PAIEMENT = "paiement"
    TYPE_SOLDE = "solde"
    TYPE_DEVOIR = "devoir"
    TYPE_EVENEMENT = "evenement"
    TYPE_LABELS = {
        TYPE_ANNONCE: "Annonce",
        TYPE_RESULTAT: "Résultat disponible",
        TYPE_ABSENCE: "Absence",
        TYPE_RETARD: "Retard",
        TYPE_CONVOCATION: "Convocation",
        TYPE_PAIEMENT: "Paiement",
        TYPE_SOLDE: "Solde",
        TYPE_DEVOIR: "Devoir",
        TYPE_EVENEMENT: "Événement",
    }

    CHANNEL_WEB = "web"
    CHANNEL_EMAIL = "email"
    CHANNEL_SMS = "sms"
    CHANNEL_WHATSAPP = "whatsapp"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    type = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.String(500), nullable=True)
    channel = db.Column(db.String(20), nullable=False, default=CHANNEL_WEB)
    related_url = db.Column(db.String(500), nullable=True)
    read_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User")

    @property
    def is_read(self):
        return self.read_at is not None

    def __repr__(self):
        return f"<Notification user={self.user_id} type={self.type}>"
