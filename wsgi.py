import os

from dotenv import load_dotenv

# Charge .env avant create_app() : python-dotenv est déjà une dépendance déclarée
# (requirements.txt) mais n'était jusqu'ici jamais réellement invoqué — un fichier .env local
# n'avait donc aucun effet, malgré .env.example qui documente de le créer. En production
# (Render, etc.), les variables d'environnement sont déjà injectées directement par la
# plateforme ; load_dotenv() n'y trouve simplement aucun fichier .env et ne fait rien.
load_dotenv()

from app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=bool(int(os.environ.get("FLASK_DEBUG", "1"))))
