"""Agrégations pour les rapports du Préfet (brief : "rapports avancés"). Ne recalcule jamais
la logique métier elle-même — chaque rapport ne fait qu'agréger ce que les services dédiés
(finance.py, grades.py, attendance.py) exposent déjà, pour ne jamais diverger des chiffres
affichés ailleurs dans l'application (dashboards, bulletins, vue Comptable).
"""

from collections import defaultdict
from decimal import Decimal

from app.models import Attendance, Classe, Enrollment, Expense, Fee, FeeType
from app.services.attendance import daily_status_by_student
from app.services.finance import active_students_query, student_balance
from app.services.grades import student_overall_average


def attendance_report(school_year, date_from, date_to):
    """Pour chaque classe : nombre de journées-élève absentes/en retard sur la période, et
    taux de présence global de la classe."""
    classes = Classe.query.filter_by(school_year_id=school_year.id).order_by(Classe.name).all()
    rows = []
    for classe in classes:
        student_ids = {
            e.student_profile_id
            for e in Enrollment.query.filter_by(classe_id=classe.id, status=Enrollment.STATUS_ACTIF).all()
        }
        if not student_ids:
            continue

        records = Attendance.query.filter(
            Attendance.classe_id == classe.id,
            Attendance.date >= date_from,
            Attendance.date <= date_to,
        ).all()

        by_date = defaultdict(list)
        for record in records:
            by_date[record.date].append(record)

        absences = 0
        retards = 0
        present_days = 0
        total_days = 0
        for _date, day_records in by_date.items():
            by_student = daily_status_by_student(day_records)
            for status in by_student.values():
                total_days += 1
                if status == Attendance.STATUS_ABSENT:
                    absences += 1
                elif status == Attendance.STATUS_RETARD:
                    retards += 1
                else:
                    present_days += 1

        taux_presence = (present_days / total_days * 100) if total_days else None
        rows.append(
            {
                "classe": classe,
                "effectif": len(student_ids),
                "absences": absences,
                "retards": retards,
                "taux_presence": taux_presence,
            }
        )
    return rows


def financial_report(school_year):
    """Totaux globaux (dû/payé/solde), répartition par type de frais, et dépenses — pour la
    vue d'ensemble financière que le Comptable/Préfet n'ont pas déjà via la vue au quotidien."""
    totals = {"due": Decimal("0"), "paid": Decimal("0"), "balance": Decimal("0")}
    for student in active_students_query(school_year):
        due, paid, balance = student_balance(student, school_year)
        totals["due"] += due
        totals["paid"] += paid
        totals["balance"] += balance

    fee_types = FeeType.query.filter_by(school_year_id=school_year.id).order_by(FeeType.label).all()
    by_fee_type = []
    for fee_type in fee_types:
        fees = Fee.query.filter_by(fee_type_id=fee_type.id, school_year_id=school_year.id).all()
        due = sum((f.amount_due for f in fees), start=Decimal("0"))
        paid = sum((f.amount_paid for f in fees), start=Decimal("0"))
        by_fee_type.append({"fee_type": fee_type, "due": due, "paid": paid, "balance": due - paid})

    expenses = Expense.query.filter_by(school_year_id=school_year.id, deleted_at=None).all()
    total_expenses = sum((e.amount for e in expenses), start=Decimal("0"))

    return {
        "totals": totals,
        "by_fee_type": by_fee_type,
        "total_expenses": total_expenses,
        "net": totals["paid"] - total_expenses,
    }


def academic_report(school_year, term):
    """Moyenne par classe et classement des 5 meilleures / 5 moins bonnes moyennes générales
    de l'établissement pour ce trimestre."""
    classes = Classe.query.filter_by(school_year_id=school_year.id).order_by(Classe.name).all()
    class_rows = []
    all_students = []

    for classe in classes:
        enrollments = Enrollment.query.filter_by(classe_id=classe.id, status=Enrollment.STATUS_ACTIF).all()
        averages = []
        for enrollment in enrollments:
            average = student_overall_average(enrollment.student_profile_id, school_year.id, term)
            if average is not None:
                averages.append(average)
                all_students.append({"student": enrollment.student, "classe": classe, "average": average})

        classe_average = sum(averages) / len(averages) if averages else None
        class_rows.append({"classe": classe, "effectif": len(enrollments), "moyenne": classe_average})

    all_students.sort(key=lambda r: r["average"], reverse=True)
    return {
        "by_classe": class_rows,
        "top5": all_students[:5],
        "bottom5": list(reversed(all_students[-5:])) if len(all_students) > 5 else [],
    }
