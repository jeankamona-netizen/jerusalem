"""Calcul des moyennes — service partagé par les vues Enseignant, Direction des Études,
Élève, Parent et par la génération de bulletins : un seul endroit qui sait comment une
moyenne est calculée, pour ne jamais la recalculer différemment selon l'écran.

Barème : chaque note est ramenée sur 20 (score / max_score * 20), pondérée par le
coefficient de l'évaluation pour la moyenne de matière, puis les moyennes de matière sont
pondérées par le coefficient par défaut de la matière pour la moyenne générale.
"""

from collections import defaultdict
from decimal import Decimal

from app.models import Assessment, Grade


def student_subject_averages(student_profile_id, school_year_id, term):
    """Retourne une liste de dicts {subject, average, grades: [Grade, ...]} pour les
    matières où l'élève a au moins une note saisie ce trimestre."""
    grades = (
        Grade.query.join(Assessment, Grade.assessment_id == Assessment.id)
        .filter(
            Grade.student_profile_id == student_profile_id,
            Assessment.school_year_id == school_year_id,
            Assessment.term == term,
            Grade.score.isnot(None),
        )
        .all()
    )

    by_subject = defaultdict(list)
    for grade in grades:
        by_subject[grade.assessment.subject_id].append(grade)

    results = []
    for subject_grades in by_subject.values():
        subject = subject_grades[0].assessment.subject
        weighted_sum = Decimal("0")
        weight_sum = Decimal("0")
        for grade in subject_grades:
            coeff = Decimal(grade.assessment.coefficient)
            normalized = Decimal(grade.score) / Decimal(grade.assessment.max_score) * 20
            weighted_sum += normalized * coeff
            weight_sum += coeff
        average = weighted_sum / weight_sum if weight_sum > 0 else None
        results.append({"subject": subject, "average": average, "grades": subject_grades})

    results.sort(key=lambda r: r["subject"].name)
    return results


def student_overall_average(student_profile_id, school_year_id, term):
    subject_averages = student_subject_averages(student_profile_id, school_year_id, term)
    weighted_sum = Decimal("0")
    weight_sum = Decimal("0")
    for row in subject_averages:
        if row["average"] is None:
            continue
        coeff = Decimal(row["subject"].default_coefficient)
        weighted_sum += row["average"] * coeff
        weight_sum += coeff
    return weighted_sum / weight_sum if weight_sum > 0 else None
