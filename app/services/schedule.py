"""Détection de conflits d'horaire et affectations enseignant↔classe — service partagé
entre la gestion (Direction des Études) et le scoping des modules Notes/Présence.

Un seul point d'entrée pour la règle de chevauchement horaire (deux créneaux se chevauchent
si le début de l'un précède la fin de l'autre et vice-versa) : elle n'est écrite qu'ici.
"""

from app.models import Schedule


def _overlaps(start_a, end_a, start_b, end_b):
    return start_a < end_b and end_a > start_b


def check_conflicts(school_year_id, classe_id, teacher_profile_id, room_id, day, start_time, end_time, exclude_id=None):
    """Retourne la liste des messages de conflit (vide si aucun). Vérifie, pour le même
    jour et la même année scolaire : le même enseignant, la même salle (si renseignée) et
    la même classe ne sont jamais programmés sur deux créneaux qui se chevauchent."""
    query = Schedule.query.filter(Schedule.school_year_id == school_year_id, Schedule.day == day)
    if exclude_id:
        query = query.filter(Schedule.id != exclude_id)

    conflicts = []
    for other in query.all():
        if not _overlaps(start_time, end_time, other.start_time, other.end_time):
            continue
        if other.teacher_profile_id == teacher_profile_id:
            conflicts.append(
                f"Conflit enseignant : {other.teacher.nom} est déjà affecté à {other.classe.name} "
                f"({other.subject.name}) de {other.start_time.strftime('%H:%M')} à {other.end_time.strftime('%H:%M')}."
            )
        if room_id and other.room_id == room_id:
            conflicts.append(
                f"Conflit de salle : {other.room.name} est déjà utilisée par {other.classe.name} "
                f"de {other.start_time.strftime('%H:%M')} à {other.end_time.strftime('%H:%M')}."
            )
        if other.classe_id == classe_id:
            conflicts.append(
                f"Conflit de classe : {other.classe.name} a déjà {other.subject.name} "
                f"de {other.start_time.strftime('%H:%M')} à {other.end_time.strftime('%H:%M')}."
            )
    return conflicts


def teacher_affectations(teacher_profile_id, school_year_id):
    """Combinaisons (classe_id, subject_id) distinctes auxquelles un enseignant est
    effectivement affecté cette année, d'après l'emploi du temps."""
    rows = Schedule.query.filter_by(teacher_profile_id=teacher_profile_id, school_year_id=school_year_id).all()
    seen = {}
    for row in rows:
        seen[(row.classe_id, row.subject_id)] = (row.classe, row.subject)
    return list(seen.values())
