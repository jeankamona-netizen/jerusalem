"""Fiche disciplinaire d'un élève — un seul endroit qui assemble présence, incidents et
convocations pour que le format reste identique partout où on la consulte (brief section 11 :
"Élève : Jean Mukendi — Absences: 4, Retards: 3, Avertissements: 1, Sanctions: 0").
"""

from app.models import Convocation, DisciplinaryAction, DisciplinaryIncident
from app.services.attendance import student_attendance_summary


def student_discipline_summary(student_profile_id, school_year_id):
    attendance = student_attendance_summary(student_profile_id, school_year_id)

    incidents = (
        DisciplinaryIncident.query.filter_by(student_profile_id=student_profile_id, school_year_id=school_year_id)
        .order_by(DisciplinaryIncident.date.desc())
        .all()
    )
    incident_ids = [incident.id for incident in incidents]
    actions = DisciplinaryAction.query.filter(DisciplinaryAction.incident_id.in_(incident_ids)).all() if incident_ids else []

    convocations = (
        Convocation.query.filter_by(student_profile_id=student_profile_id)
        .order_by(Convocation.date.desc())
        .all()
    )

    return {
        "absences": attendance["absences"],
        "retards": attendance["retards"],
        "avertissements": sum(1 for a in actions if a.type == DisciplinaryAction.TYPE_AVERTISSEMENT),
        "sanctions": sum(1 for a in actions if a.type == DisciplinaryAction.TYPE_SANCTION),
        "exclusions": sum(1 for a in actions if a.type == DisciplinaryAction.TYPE_EXCLUSION),
        "incidents": incidents,
        "convocations": convocations,
    }
