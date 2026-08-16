"""Service central de notifications (brief section 25).

Architecture extensible par conception : chaque canal a un "dispatcher" dans
`CHANNEL_DISPATCHERS`. `web` est livré depuis le P1 (création d'une ligne `Notification`,
visible dans `/notifications`). `email` est réellement branché (SMTP, voir `_deliver_email`)
mais reste en mode "log seulement" tant que `MAIL_SERVER` n'est pas configuré en variable
d'environnement — comportement volontaire pour ne pas casser un déploiement qui n'a pas
encore de serveur mail. SMS/WhatsApp restent des stubs : brancher un vrai fournisseur
(Africa's Talking, Twilio, WhatsApp Cloud API...) nécessite un choix de fournisseur et des
identifiants que seul l'établissement peut fournir. Brancher un canal plus tard ne change
aucun des appels à `notify()` dans le reste du code — seul son dispatcher est remplacé.
"""

import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

from app.extensions import db
from app.models import Notification

logger = logging.getLogger("csj.notifications")


def _deliver_web(notification):
    # La ligne Notification existe déjà à ce stade — c'est elle, la livraison "web".
    return True


def _deliver_email(notification):
    mail_server = current_app.config.get("MAIL_SERVER")
    if not mail_server:
        logger.info(
            "MAIL_SERVER non configuré — notification email #%s non envoyée (voir .env.example).",
            notification.id,
        )
        return False

    recipient = notification.user.email
    if not recipient:
        return False

    message = EmailMessage()
    message["Subject"] = notification.title
    message["From"] = current_app.config["MAIL_DEFAULT_SENDER"]
    message["To"] = recipient
    body = notification.body or notification.title
    if notification.related_url:
        body += f"\n\nVoir sur le portail : {notification.related_url}"
    message.set_content(body)

    try:
        with smtplib.SMTP(mail_server, current_app.config["MAIL_PORT"], timeout=10) as smtp:
            if current_app.config["MAIL_USE_TLS"]:
                smtp.starttls()
            if current_app.config["MAIL_USERNAME"]:
                smtp.login(current_app.config["MAIL_USERNAME"], current_app.config["MAIL_PASSWORD"])
            smtp.send_message(message)
        return True
    except (smtplib.SMTPException, OSError):
        logger.exception("Échec d'envoi de la notification email #%s.", notification.id)
        return False


def _stub_dispatcher(channel_name):
    def _deliver(notification):
        logger.info(
            "Canal %s pas encore branché à un fournisseur réel — notification #%s non envoyée hors plateforme.",
            channel_name,
            notification.id,
        )
        return False

    return _deliver


CHANNEL_DISPATCHERS = {
    Notification.CHANNEL_WEB: _deliver_web,
    Notification.CHANNEL_EMAIL: _deliver_email,
    Notification.CHANNEL_SMS: _stub_dispatcher(Notification.CHANNEL_SMS),
    Notification.CHANNEL_WHATSAPP: _stub_dispatcher(Notification.CHANNEL_WHATSAPP),
}


def notify(user, notif_type, title, body=None, related_url=None, channels=(Notification.CHANNEL_WEB,)):
    """Crée une notification pour `user` sur chacun des `channels` demandés et la fait
    passer par son dispatcher. Ne fait rien si `user` est None (ex: parent sans compte de
    connexion) — appelant n'a pas besoin de vérifier avant d'appeler."""
    if user is None:
        return []

    created = []
    for channel in channels:
        notification = Notification(
            user_id=user.id,
            type=notif_type,
            title=title,
            body=body,
            channel=channel,
            related_url=related_url,
        )
        db.session.add(notification)
        db.session.flush()
        created.append(notification)

        dispatcher = CHANNEL_DISPATCHERS.get(channel, _stub_dispatcher(channel))
        dispatcher(notification)

    return created
