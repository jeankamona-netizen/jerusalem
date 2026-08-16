"""Statistiques de présence — service partagé par les dashboards Préfet/Discipline et les
vues Élève/Parent : un seul endroit qui décide comment on résume "la journée" d'un élève
quand plusieurs appels (un par matière) ont pu être pris le même jour.

Règle : si un élève a au moins un ABSENT ce jour-là, la journée compte comme absence ; sinon
au moins un RETARD compte comme retard ; sinon PRESENT. Évite de compter un même élève
plusieurs fois quand l'appel est pris par matière.
"""

from app.models import Attendance
from app.services.finance import active_students_query

_STATUS_PRIORITY = {
    Attendance.STATUS_PRESENT: 0,
    Attendance.STATUS_RETARD: 1,
    Attendance.STATUS_ABSENT: 2,
}


def daily_status_by_student(records):
    by_student = {}
    for record in records:
        current = by_student.get(record.student_profile_id)
        if current is None or _STATUS_PRIORITY[record.status] > _STATUS_PRIORITY[current]:
            by_student[record.student_profile_id] = record.status
    return by_student


def daily_school_stats(school_year, date):
    records = Attendance.query.filter_by(school_year_id=school_year.id, date=date).all()
    by_student = daily_status_by_student(records)

    counts = {Attendance.STATUS_PRESENT: 0, Attendance.STATUS_ABSENT: 0, Attendance.STATUS_RETARD: 0}
    for status in by_student.values():
        counts[status] += 1

    total_active = active_students_query(school_year).count()
    taux_presence = (counts[Attendance.STATUS_PRESENT] / total_active * 100) if total_active else None

    return {
        "present": counts[Attendance.STATUS_PRESENT],
        "absent": counts[Attendance.STATUS_ABSENT],
        "retard": counts[Attendance.STATUS_RETARD],
        "total_active": total_active,
        "total_recorded": len(by_student),
        "taux_presence": taux_presence,
    }


def student_attendance_summary(student_profile_id, school_year_id):
    records = Attendance.query.filter_by(student_profile_id=student_profile_id, school_year_id=school_year_id).all()
    by_date = {}
    for record in records:
        current = by_date.get(record.date)
        if current is None or _STATUS_PRIORITY[record.status] > _STATUS_PRIORITY[current]:
            by_date[record.date] = record.status

    counts = {Attendance.STATUS_PRESENT: 0, Attendance.STATUS_ABSENT: 0, Attendance.STATUS_RETARD: 0}
    for status in by_date.values():
        counts[status] += 1

    return {
        "present": counts[Attendance.STATUS_PRESENT],
        "absences": counts[Attendance.STATUS_ABSENT],
        "retards": counts[Attendance.STATUS_RETARD],
    }
