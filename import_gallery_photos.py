"""Importe les photos déposées dans le dossier `photos_ecole/` (à la racine du projet) dans
la galerie du site public. Idempotent : une photo déjà importée (même nom de fichier) n'est
pas dupliquée si le script est relancé après un nouvel ajout de photos.

Usage :
    1. Créer le dossier `photos_ecole/` à la racine du projet (à côté de seed_demo.py).
    2. Y déposer des photos (.jpg, .jpeg, .png, .webp).
    3. Lancer : python import_gallery_photos.py
"""

import os

from app import create_app
from app.extensions import db
from app.models import Document, School
from app.services.uploads import UploadError, import_local_file_as_document

PHOTOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos_ecole")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def run():
    app = create_app()
    with app.app_context():
        if not os.path.isdir(PHOTOS_DIR):
            os.makedirs(PHOTOS_DIR, exist_ok=True)
            print(f"Dossier créé : {PHOTOS_DIR}")
            print("Dépose tes photos dedans puis relance ce script.")
            return

        school = School.query.first()
        if not school:
            print("Aucune école configurée en base — lance d'abord seed_demo.py.")
            return

        already_imported = {
            d.original_filename
            for d in Document.query.filter_by(owner_type="Gallery", owner_id=school.id).all()
        }

        candidates = sorted(
            f for f in os.listdir(PHOTOS_DIR)
            if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS
        )

        imported_count = 0
        for filename in candidates:
            if filename in already_imported:
                continue
            source_path = os.path.join(PHOTOS_DIR, filename)
            try:
                import_local_file_as_document(source_path, "Gallery", school.id, "photo")
                imported_count += 1
                print(f"  + {filename}")
            except UploadError as exc:
                print(f"  ! {filename} ignorée : {exc}")

        db.session.commit()

        if imported_count:
            print(f"{imported_count} nouvelle(s) photo(s) importée(s) dans la galerie.")
        else:
            print("Aucune nouvelle photo à importer (tout est déjà à jour).")


if __name__ == "__main__":
    run()
