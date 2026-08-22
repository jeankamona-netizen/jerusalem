from app.extensions import db
from app.models.mixins import TimestampMixin


class Announcement(db.Model, TimestampMixin):
    """Actualité publiée sur le site public. Reste en brouillon (non visible publiquement)
    tant que le Préfet ne la publie pas explicitement — évite qu'une actualité en cours de
    rédaction n'apparaisse prématurément."""

    __tablename__ = "announcements"

    STATUS_BROUILLON = "brouillon"
    STATUS_PUBLIE = "publie"
    STATUS_CHOICES = (STATUS_BROUILLON, STATUS_PUBLIE)
    STATUS_LABELS = {STATUS_BROUILLON: "Brouillon", STATUS_PUBLIE: "Publié"}

    CATEGORY_GENERAL = "general"
    CATEGORY_ACADEMIQUE = "academique"
    CATEGORY_EVENEMENT = "evenement"
    CATEGORY_CHOICES = (CATEGORY_GENERAL, CATEGORY_ACADEMIQUE, CATEGORY_EVENEMENT)
    CATEGORY_LABELS = {
        CATEGORY_GENERAL: "Général",
        CATEGORY_ACADEMIQUE: "Académique",
        CATEGORY_EVENEMENT: "Événement",
    }

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(20), nullable=False, default=CATEGORY_GENERAL)
    status = db.Column(db.String(20), nullable=False, default=STATUS_BROUILLON)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)

    author = db.relationship("User")

    def __repr__(self):
        return f"<Announcement {self.title} status={self.status}>"


class Event(db.Model, TimestampMixin):
    """Événement du calendrier scolaire affiché publiquement (portes ouvertes, remise des
    bulletins, fêtes de l'école, etc.). Pas de cycle brouillon/publié : un événement créé est
    visible dès sa création, l'information n'a pas besoin d'être affinée avant diffusion."""

    __tablename__ = "events"

    CATEGORY_ACADEMIQUE = "academique"
    CATEGORY_CULTUREL = "culturel"
    CATEGORY_RELIGIEUX = "religieux"
    CATEGORY_AUTRE = "autre"
    CATEGORY_CHOICES = (CATEGORY_ACADEMIQUE, CATEGORY_CULTUREL, CATEGORY_RELIGIEUX, CATEGORY_AUTRE)
    CATEGORY_LABELS = {
        CATEGORY_ACADEMIQUE: "Académique",
        CATEGORY_CULTUREL: "Culturel",
        CATEGORY_RELIGIEUX: "Religieux",
        CATEGORY_AUTRE: "Autre",
    }

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(1000), nullable=True)
    date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(20), nullable=False, default=CATEGORY_AUTRE)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)

    created_by = db.relationship("User")

    def __repr__(self):
        return f"<Event {self.title} date={self.date}>"


class NewsletterSubscriber(db.Model, TimestampMixin):
    """Inscription à la newsletter depuis le site public. Capture uniquement l'email pour
    l'instant — l'envoi réel de newsletters n'est pas encore implémenté (même logique que les
    canaux SMS/WhatsApp des notifications : l'architecture de collecte existe, l'envoi viendra
    plus tard sans que cette table ait besoin de changer)."""

    __tablename__ = "newsletter_subscribers"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<NewsletterSubscriber {self.email}>"


class ContactMessage(db.Model, TimestampMixin):
    """Message envoyé depuis le formulaire « Nous contacter » du site public. Consultable par
    le Préfet (même logique de supervision globale que les préinscriptions/actualités) —
    aucune réponse automatique n'est envoyée, un humain doit rappeler/répondre par
    téléphone/email."""

    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(2000), nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<ContactMessage {self.subject} from={self.email}>"
