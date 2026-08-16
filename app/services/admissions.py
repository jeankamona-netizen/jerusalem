"""Conversion d'un dossier de préinscription accepté en élève réel — logique isolée ici
car elle touche plusieurs tables (StudentProfile, Enrollment, Application) et ne doit
jamais être dupliquée entre un futur écran d'admission en masse et l'écran actuel.
"""

from app.extensions import db
from app.models import Application, Enrollment, StudentProfile
from app.models.mixins import utcnow


def accept_application(application, decided_by_user, comment=None):
    if application.classe_demandee is None:
        raise ValueError("Impossible d'accepter : aucune classe demandée valide sur ce dossier.")

    school_year = application.classe_demandee.school_year

    student = StudentProfile(
        school_id=application.school_id,
        nom=application.nom,
        postnom=application.postnom,
        prenom=application.prenom,
        sexe=application.sexe,
        date_naissance=application.date_naissance,
        lieu_naissance=application.lieu_naissance,
        nationalite=application.nationalite,
        adresse=application.adresse,
        ancienne_ecole=application.ancienne_ecole,
        is_demo=application.is_demo,
    )
    db.session.add(student)
    db.session.flush()

    db.session.add(
        Enrollment(
            student_profile_id=student.id,
            classe_id=application.classe_demandee_id,
            school_year_id=school_year.id,
            status=Enrollment.STATUS_ACTIF,
        )
    )

    application.status = Application.STATUS_ACCEPTE
    application.decision_comment = comment
    application.decided_at = utcnow()
    application.decided_by_user_id = decided_by_user.id
    application.resulting_student_profile_id = student.id

    return student
