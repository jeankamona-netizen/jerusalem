import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# FLASK_ENV=development est le SEUL moyen d'autoriser des valeurs de secours pour les secrets
# (SECRET_KEY, mot de passe admin). Par défaut (variable absente, ex. en production), le
# démarrage échoue si un secret requis n'est pas défini — voir _exiger_secret() ci-dessous.
# Même convention que le projet Majt Shop (app.py:exiger_secret), pour ne jamais déployer
# accidentellement avec des identifiants par défaut publics (visibles dans ce dépôt).
_EST_DEV = os.environ.get("FLASK_ENV", "").strip().lower() == "development"


def _exiger_secret(nom_variable, valeur_dev):
    valeur = os.environ.get(nom_variable)
    if valeur:
        return valeur
    if _EST_DEV:
        return valeur_dev
    raise RuntimeError(
        f"{nom_variable} doit être définie via une variable d'environnement pour démarrer "
        "l'application. En local, définissez FLASK_ENV=development pour utiliser une valeur "
        "de secours de développement."
    )


def _default_sqlite_url():
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    return f"sqlite:///{data_dir / 'csj_dev.db'}"


class Config:
    SECRET_KEY = _exiger_secret("SECRET_KEY", "dev-csj-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or _default_sqlite_url()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WTF_CSRF_ENABLED = True

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 Mo max par upload
    ALLOWED_UPLOAD_MIME_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    }

    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@csjerusalem.cd")
    ADMIN_MOT_DE_PASSE = _exiger_secret("ADMIN_MOT_DE_PASSE", "ChangeMoi2026!")

    # Canal email des notifications (app/services/notifications.py). Non configuré par défaut
    # (MAIL_SERVER vide) — le dispatcher email reste alors en mode "log seulement", comme les
    # canaux SMS/WhatsApp, jusqu'à ce que l'établissement fournisse un serveur SMTP réel.
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "1") == "1"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "CS Jérusalem <no-reply@csjerusalem.cd>")

    SCHOOL_NAME = "CS Jérusalem"
    SCHOOL_CITY = "Lubumbashi"
    SCHOOL_PROVINCE = "Haut-Katanga"
    SCHOOL_COUNTRY = "RDC"
    SCHOOL_CURRENCY_DEFAULT = "CDF"
