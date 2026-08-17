import datetime
import mimetypes
import os

from flask import abort, flash, redirect, render_template, send_file, url_for

from app.blueprints.public import public_bp
from app.blueprints.public.forms import ApplicationForm
from app.extensions import db, limiter
from app.models import Announcement, Application, Classe, Document, Event, School
from app.services.audit import log_action
from app.services.pdf import next_document_number
from app.services.school_year import get_current_school_year
from app.services.uploads import UploadError, validate_and_save_upload


# Sélection de photos réelles de l'école pour le défilement de la page d'accueil — choisies
# à la main pour leur diversité (vie de classe, ateliers pratiques, culte, célébration) plutôt
# que les N premières importées, qui peuvent se ressembler (série de photos prises à la suite).
CAROUSEL_FILENAMES = [
    "IMG_20240902_083613_801.jpg",
    "IMG_20240130_144020_943.jpg",
    "IMG_20240927_093441_134.jpg",
    "IMG_20250130_101819_112.jpg",
    "IMG_20250130_102123_357.jpg",
    "IMG_20241219_104006_661.jpg",
    "IMG_20250308_144405_380.jpg",
    "IMG_20250308_144529_351.jpg",
]


@public_bp.route("/")
def home():
    latest = (
        Announcement.query.filter_by(status=Announcement.STATUS_PUBLIE)
        .order_by(Announcement.published_at.desc())
        .limit(3)
        .all()
    )
    upcoming_events = (
        Event.query.filter(Event.date >= datetime.date.today()).order_by(Event.date.asc()).limit(3).all()
    )
    images_by_event = {
        d.owner_id: d for d in Document.query.filter_by(owner_type="Event", category="image").all()
    }
    images_by_announcement = {
        d.owner_id: d for d in Document.query.filter_by(owner_type="Announcement", category="image").all()
    }

    carousel_documents = Document.query.filter(
        Document.owner_type == "Gallery",
        Document.category == "photo",
        Document.original_filename.in_(CAROUSEL_FILENAMES),
    ).all()
    by_filename = {d.original_filename: d for d in carousel_documents}
    carousel_images = [
        url_for("public.gallery_image", document_id=by_filename[name].id)
        for name in CAROUSEL_FILENAMES
        if name in by_filename
    ]

    # Aperçu galerie sur l'accueil : les 6 photos les plus récentes (mêmes sources que /galerie
    # — annonces publiées + photothèque), pas seulement la sélection fixe du carrousel.
    gallery_announcement_docs = (
        Document.query.filter_by(owner_type="Announcement", category="image")
        .join(Announcement, Announcement.id == Document.owner_id)
        .filter(Announcement.status == Announcement.STATUS_PUBLIE)
        .all()
    )
    gallery_photo_docs = Document.query.filter_by(owner_type="Gallery", category="photo").all()
    gallery_preview = sorted(
        gallery_announcement_docs + gallery_photo_docs, key=lambda d: d.created_at, reverse=True
    )[:6]
    gallery_preview_urls = [
        url_for("public.news_image", document_id=d.id)
        if d.owner_type == "Announcement"
        else url_for("public.gallery_image", document_id=d.id)
        for d in gallery_preview
    ]

    return render_template(
        "public/home.html",
        latest_announcements=latest,
        upcoming_events=upcoming_events,
        images_by_event=images_by_event,
        images_by_announcement=images_by_announcement,
        carousel_images=carousel_images,
        gallery_preview_urls=gallery_preview_urls,
    )


@public_bp.route("/logo")
def logo():
    """Logo de l'établissement : sert `School.logo_path` s'il a été téléversé par le Super
    Admin (`/admin/parametres`), sinon retombe sur le logo statique par défaut du dépôt —
    un établissement qui n'a jamais changé son logo continue de fonctionner sans réglage."""
    school = School.query.first()
    if school and school.logo_path and os.path.exists(school.logo_path):
        mime_type, _ = mimetypes.guess_type(school.logo_path)
        return send_file(school.logo_path, mimetype=mime_type or "image/jpeg")
    return redirect(url_for("static", filename="img/logo.jpg"))


@public_bp.route("/a-propos")
def about():
    return render_template("public/about.html")


@public_bp.route("/vie-scolaire")
def school_life():
    return render_template("public/school_life.html")


@public_bp.route("/actualites")
def news():
    announcements = (
        Announcement.query.filter_by(status=Announcement.STATUS_PUBLIE)
        .order_by(Announcement.published_at.desc())
        .all()
    )
    upcoming_events = (
        Event.query.filter(Event.date >= datetime.date.today()).order_by(Event.date.asc()).all()
    )
    images_by_announcement = {
        d.owner_id: d for d in Document.query.filter_by(owner_type="Announcement", category="image").all()
    }
    images_by_event = {
        d.owner_id: d for d in Document.query.filter_by(owner_type="Event", category="image").all()
    }
    return render_template(
        "public/news.html",
        announcements=announcements,
        upcoming_events=upcoming_events,
        images_by_announcement=images_by_announcement,
        images_by_event=images_by_event,
    )


@public_bp.route("/actualites/<int:announcement_id>")
def news_detail(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    if announcement.status != Announcement.STATUS_PUBLIE:
        abort(404)
    image = Document.query.filter_by(
        owner_type="Announcement", owner_id=announcement.id, category="image"
    ).first()
    return render_template("public/news_detail.html", announcement=announcement, image=image)


@public_bp.route("/actualites/images/<int:document_id>")
def news_image(document_id):
    document = Document.query.get_or_404(document_id)
    if document.owner_type != "Announcement":
        abort(404)
    announcement = Announcement.query.get_or_404(document.owner_id)
    if announcement.status != Announcement.STATUS_PUBLIE:
        abort(404)
    if not os.path.exists(document.file_path):
        abort(404)
    return send_file(document.file_path, mimetype=document.mime_type)


@public_bp.route("/evenements/images/<int:document_id>")
def event_image(document_id):
    document = Document.query.filter_by(id=document_id, owner_type="Event", category="image").first_or_404()
    if not os.path.exists(document.file_path):
        abort(404)
    return send_file(document.file_path, mimetype=document.mime_type)


@public_bp.route("/galerie")
def gallery():
    announcement_images = (
        Document.query.filter_by(owner_type="Announcement", category="image")
        .join(Announcement, Announcement.id == Document.owner_id)
        .filter(Announcement.status == Announcement.STATUS_PUBLIE)
        .all()
    )
    gallery_photos = Document.query.filter_by(owner_type="Gallery", category="photo").all()
    documents = sorted(announcement_images + gallery_photos, key=lambda d: d.created_at, reverse=True)
    images = [
        {
            "url": url_for("public.news_image", document_id=d.id)
            if d.owner_type == "Announcement"
            else url_for("public.gallery_image", document_id=d.id)
        }
        for d in documents
    ]
    return render_template("public/gallery.html", images=images)


@public_bp.route("/galerie/images/<int:document_id>")
def gallery_image(document_id):
    document = Document.query.filter_by(id=document_id, owner_type="Gallery", category="photo").first_or_404()
    if not os.path.exists(document.file_path):
        abort(404)
    return send_file(document.file_path, mimetype=document.mime_type)


@public_bp.route("/preinscription", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def application_new():
    school = School.query.first()
    school_year = get_current_school_year(school.id) if school else None

    form = ApplicationForm()
    classes = Classe.query.filter_by(school_year_id=school_year.id).order_by(Classe.name).all() if school_year else []
    form.classe_demandee_id.choices = [(c.id, c.name) for c in classes]

    if not school or not school_year or not classes:
        flash("La préinscription n'est pas disponible pour le moment. Merci de contacter l'établissement.", "error")
        return render_template("public/application_new.html", form=None)

    if form.validate_on_submit():
        application = Application(
            school_id=school.id,
            number=next_document_number(Application, datetime.date.today().year),
            nom=form.nom.data.strip(),
            postnom=form.postnom.data.strip() if form.postnom.data else None,
            prenom=form.prenom.data.strip() if form.prenom.data else None,
            sexe=form.sexe.data,
            date_naissance=form.date_naissance.data,
            lieu_naissance=form.lieu_naissance.data or None,
            nationalite=form.nationalite.data or "Congolaise",
            adresse=form.adresse.data or None,
            ancienne_ecole=form.ancienne_ecole.data or None,
            classe_demandee_id=form.classe_demandee_id.data,
            parent_nom=form.parent_nom.data.strip(),
            parent_telephone=form.parent_telephone.data.strip(),
            parent_email=form.parent_email.data.strip() if form.parent_email.data else None,
            parent_adresse=form.parent_adresse.data or None,
            parent_relation=form.parent_relation.data,
        )
        db.session.add(application)
        db.session.flush()

        try:
            if form.photo.data and form.photo.data.filename:
                validate_and_save_upload(form.photo.data, "Application", application.id, "photo")
            if form.document_scolaire.data and form.document_scolaire.data.filename:
                validate_and_save_upload(form.document_scolaire.data, "Application", application.id, "document_scolaire")
        except UploadError as exc:
            db.session.rollback()
            flash(str(exc), "error")
            return render_template("public/application_new.html", form=form)

        db.session.commit()
        log_action("application_submitted", entity_type="Application", entity_id=application.id)
        return redirect(url_for("public.application_confirmation", number=application.number))

    return render_template("public/application_new.html", form=form)


@public_bp.route("/preinscription/confirmation/<number>")
def application_confirmation(number):
    application = Application.query.filter_by(number=number).first()
    if not application:
        abort(404)
    return render_template("public/application_confirmation.html", application=application)
