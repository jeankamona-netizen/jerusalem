"""Journalisation des actions sensibles (brief section 29) : connexion, note modifiée, élève
modifié, suppression, paiement, sanction, changement de rôle, etc.

Point d'entrée unique : chaque appelant appelle `log_action(...)` de la même façon depuis
n'importe quel module, sans jamais écrire dans `AuditLog` directement. Chaque site d'appel
commite déjà sa propre transaction métier avant d'appeler `log_action` (vérifié sur les ~40
appels existants) — la ligne d'audit est donc commitée séparément ici sans jamais risquer
d'annuler ou d'être annulée par le changement métier qu'elle documente.
"""

import logging

from flask import request
from flask_login import current_user

from app.extensions import db
from app.models import AuditLog

audit_logger = logging.getLogger("csj.audit")


def log_action(action, entity_type=None, entity_id=None, old_value=None, new_value=None):
    user_id = current_user.id if current_user and current_user.is_authenticated else None
    ip = request.remote_addr if request else None
    audit_logger.info(
        "action=%s user_id=%s entity_type=%s entity_id=%s ip=%s old=%s new=%s",
        action,
        user_id,
        entity_type,
        entity_id,
        ip,
        old_value,
        new_value,
    )
    db.session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            ip=ip,
        )
    )
    db.session.commit()
