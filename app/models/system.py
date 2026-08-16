from app.extensions import db
from app.models.mixins import utcnow


class AuditLog(db.Model):
    """Journal des actions sensibles (brief section 29) : connexion, modification de note,
    d'élève, suppression, paiement, sanction, changement de rôle, etc. Écrit exclusivement
    via `app/services/audit.py:log_action()` — jamais directement — pour garder un seul
    point d'entrée cohérent. Pas de `updated_at` : une entrée de journal est immuable, elle
    ne se modifie jamais après coup."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    old_value = db.Column(db.JSON, nullable=True)
    new_value = db.Column(db.JSON, nullable=True)
    ip = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    user = db.relationship("User")

    def __repr__(self):
        return f"<AuditLog {self.action} user={self.user_id}>"
