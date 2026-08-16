"""Validation et stockage des fichiers uploadés (brief section 37 : type MIME, taille
maximale, jamais de confiance aveugle dans un upload public).

`MAX_CONTENT_LENGTH` (config) plafonne déjà la requête entière côté Flask/Werkzeug ; ce
module ajoute une vérification par fichier (type MIME déclaré + taille réelle lue depuis le
flux, pas la valeur `Content-Length` fournie par le client) avant d'écrire quoi que ce soit
sur disque.
"""

import mimetypes
import os
import shutil
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Document

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 Mo par fichier


class UploadError(ValueError):
    pass


def validate_and_save_upload(file_storage, owner_type, owner_id, category, uploaded_by_user_id=None):
    if not file_storage or not file_storage.filename:
        return None

    mime_type = file_storage.mimetype
    if mime_type not in current_app.config["ALLOWED_UPLOAD_MIME_TYPES"]:
        raise UploadError(f"Type de fichier non autorisé pour « {category} » ({mime_type}).")

    file_storage.stream.seek(0, os.SEEK_END)
    size_bytes = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise UploadError(f"Fichier « {category} » trop volumineux (max {MAX_FILE_SIZE_BYTES // (1024 * 1024)} Mo).")
    if size_bytes == 0:
        raise UploadError(f"Fichier « {category} » vide.")

    upload_dir = os.path.join(current_app.instance_path, "uploads", owner_type.lower())
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = secure_filename(file_storage.filename)
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = os.path.join(upload_dir, stored_name)
    file_storage.save(file_path)

    document = Document(
        owner_type=owner_type,
        owner_id=owner_id,
        category=category,
        file_path=file_path,
        original_filename=safe_name,
        mime_type=mime_type,
        size_bytes=size_bytes,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db.session.add(document)
    return document


def import_local_file_as_document(source_path, owner_type, owner_id, category, uploaded_by_user_id=None):
    """Même validation et même convention de stockage que `validate_and_save_upload`, mais à
    partir d'un fichier déjà présent sur disque (photothèque école déposée localement par
    l'équipe) plutôt qu'un upload HTTP — utilisé par le script d'import de la galerie."""
    if not os.path.isfile(source_path):
        raise UploadError(f"Fichier introuvable : {source_path}")

    mime_type, _ = mimetypes.guess_type(source_path)
    if mime_type not in current_app.config["ALLOWED_UPLOAD_MIME_TYPES"]:
        raise UploadError(f"Type de fichier non autorisé pour « {os.path.basename(source_path)} » ({mime_type}).")

    size_bytes = os.path.getsize(source_path)
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise UploadError(
            f"Fichier « {os.path.basename(source_path)} » trop volumineux "
            f"(max {MAX_FILE_SIZE_BYTES // (1024 * 1024)} Mo)."
        )
    if size_bytes == 0:
        raise UploadError(f"Fichier « {os.path.basename(source_path)} » vide.")

    upload_dir = os.path.join(current_app.instance_path, "uploads", owner_type.lower())
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = secure_filename(os.path.basename(source_path))
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    dest_path = os.path.join(upload_dir, stored_name)
    shutil.copyfile(source_path, dest_path)

    document = Document(
        owner_type=owner_type,
        owner_id=owner_id,
        category=category,
        file_path=dest_path,
        original_filename=safe_name,
        mime_type=mime_type,
        size_bytes=size_bytes,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db.session.add(document)
    return document
