"""Génération de documents PDF (reçus, bulletins plus tard) via xhtml2pdf.

xhtml2pdf est pur Python (s'appuie sur ReportLab) : contrairement à WeasyPrint, il ne
nécessite aucune bibliothèque native (GTK/Pango) absente par défaut sur Windows et sur de
nombreux environnements d'hébergement simples. Les modèles vivent dans des templates HTML
(`templates/pdf/*.html`), modifiables sans toucher au code Python — seule la mise en page
(sous-ensemble CSS supporté par xhtml2pdf : pas de flexbox/grid) doit rester simple.
"""

import io
import os

from flask import current_app, render_template
from xhtml2pdf import pisa

from app import constants


def render_pdf(template_name, **context):
    html = render_template(template_name, **context)
    buffer = io.BytesIO()
    result = pisa.CreatePDF(io.StringIO(html), dest=buffer)
    if result.err:
        raise RuntimeError(f"Échec de génération PDF pour {template_name} (code {result.err})")
    return buffer.getvalue()


def next_document_number(model, year):
    """CSJ-<année>-XXXXX, séquentiel par année. Suffisant pour le volume d'un établissement
    secondaire (encodage par un nombre restreint de comptables/agents) ; à revoir avec un
    verrou/une séquence base de données si le volume augmente fortement."""
    prefix = f"CSJ-{year}-"
    count = model.query.filter(model.number.like(f"{prefix}%")).count()
    return f"{prefix}{count + 1:05d}"


def receipt_pdf_path(receipt_number):
    receipts_dir = os.path.join(current_app.instance_path, "receipts")
    os.makedirs(receipts_dir, exist_ok=True)
    return os.path.join(receipts_dir, f"{receipt_number}.pdf")


def generate_and_save_receipt(payment, receipt, school):
    pdf_bytes = render_pdf(
        "pdf/receipt.html",
        payment=payment,
        receipt=receipt,
        student=payment.student,
        school=school,
    )
    path = receipt_pdf_path(receipt.number)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return path


def bulletin_pdf_path(report_card):
    bulletins_dir = os.path.join(current_app.instance_path, "bulletins")
    os.makedirs(bulletins_dir, exist_ok=True)
    return os.path.join(
        bulletins_dir, f"{report_card.student_profile_id}-{report_card.school_year_id}-{report_card.term}.pdf"
    )


def generate_and_save_bulletin(report_card, student, school, school_year, subject_averages, overall_average):
    pdf_bytes = render_pdf(
        "pdf/bulletin.html",
        report_card=report_card,
        student=student,
        school=school,
        school_year=school_year,
        subject_averages=subject_averages,
        overall_average=overall_average,
        term_label=constants.TERM_LABELS.get(report_card.term, report_card.term),
    )
    path = bulletin_pdf_path(report_card)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return path
