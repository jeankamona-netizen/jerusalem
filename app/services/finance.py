"""Calculs financiers partagés entre le module Comptable (gestion) et la vue Préfet
(lecture seule globale) — un seul point de vérité pour ne jamais faire diverger les deux.
"""

from decimal import Decimal

from app.models import Enrollment, Fee, StudentProfile


def active_students_query(school_year):
    return (
        StudentProfile.query.join(Enrollment, Enrollment.student_profile_id == StudentProfile.id)
        .filter(
            Enrollment.school_year_id == school_year.id,
            Enrollment.status == Enrollment.STATUS_ACTIF,
            StudentProfile.deleted_at.is_(None),
        )
        .order_by(StudentProfile.nom)
    )


def student_balance(student, school_year):
    fees = Fee.query.filter_by(student_profile_id=student.id, school_year_id=school_year.id).all()
    due = sum((f.amount_due for f in fees), start=Decimal("0"))
    paid = sum((f.amount_paid for f in fees), start=Decimal("0"))
    return due, paid, due - paid
