"""Jeu de données DEMO pour le portail CS Jérusalem.

Toutes les entités créées ici (utilisateurs, élèves, parents, enseignants) sont marquées
`is_demo=True` pour rester clairement séparées des données réelles de l'établissement
(brief section 46). Le compte SUPER_ADMIN (issu de ADMIN_EMAIL/ADMIN_MOT_DE_PASSE) n'est
PAS marqué démo : c'est le compte réel d'exploitation.

Usage :
    python seed_demo.py
"""

import datetime
import os

from app import create_app
from app import constants
from app.extensions import db
from app.models import (
    Announcement,
    Application,
    Assessment,
    AssessmentType,
    Attendance,
    Classe,
    Convocation,
    CourseMaterial,
    DisciplinaryAction,
    DisciplinaryIncident,
    Enrollment,
    Event,
    Expense,
    Fee,
    FeeType,
    Grade,
    Homework,
    Notification,
    ParentProfile,
    ParentStudent,
    Payment,
    Permission,
    Receipt,
    ReportCard,
    Role,
    RolePermission,
    Room,
    Schedule,
    School,
    SchoolYear,
    StaffProfile,
    StudentProfile,
    Subject,
    TeacherProfile,
    User,
)
from app.models import Document
from app.models.mixins import utcnow
from app.services.admissions import accept_application
from app.services.grades import student_overall_average, student_subject_averages
from app.services.notifications import notify
from app.services.pdf import generate_and_save_bulletin, generate_and_save_receipt, next_document_number
from app.services.schedule import check_conflicts
from app.services.uploads import UploadError, import_local_file_as_document

DEMO_PASSWORD = "Demo2026!"

PHOTOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos_ecole")


def attach_photo_if_available(owner_type, owner_id, filename):
    """Attache une vraie photo d'école (déposée dans photos_ecole/, voir
    import_gallery_photos.py) comme illustration d'une actualité ou d'un événement démo, si le
    fichier est présent — silencieux sinon (les photos sont un dépôt manuel de l'équipe, pas
    garanties présentes sur toutes les machines de dev)."""
    already = Document.query.filter_by(owner_type=owner_type, owner_id=owner_id, category="image").first()
    if already:
        return
    source_path = os.path.join(PHOTOS_DIR, filename)
    if not os.path.isfile(source_path):
        return
    try:
        import_local_file_as_document(source_path, owner_type, owner_id, "image")
    except UploadError:
        pass

PREFET_NOM = "Mwamba Kalenga"
DIRECTEUR_ETUDES_NOM = "Ilunga Mutombo"
DIRECTEUR_DISCIPLINE_NOM = "Kabeya Ntumba"

TEACHER_NAMES = [
    "Kasongo Mbayo",
    "Tshibangu Kalala",
    "Mulumba Kanku",
    "Ngoyi Banza",
    "Kayembe Ditend",
]

COMPTABLE_NAMES = ["Mbuyi Kasongo", "Kalonji Mukendi"]

STUDENT_FIRST_NAMES = [
    "Jean", "Grace", "David", "Esther", "Joseph", "Bénédicte", "Emmanuel", "Christelle",
    "Patrick", "Nadège", "Trésor", "Divine", "Élie", "Rachel", "Samuel", "Judith",
    "Moïse", "Sarah", "Daniel", "Ruth",
]
STUDENT_LAST_NAMES = [
    "Mukendi", "Kalala", "Tshimanga", "Ilunga", "Kabongo", "Mwenze", "Nkulu", "Kazadi",
    "Banza", "Mutombo", "Kanyinda", "Lumbala", "Ngalula", "Kapinga", "Mbala", "Kasongo",
    "Mulaja", "Kabeya", "Ntumba", "Kayembe",
]

PARENT_NAMES = [
    "Mukendi Ferdinand", "Kalala Béatrice", "Tshimanga Robert", "Ilunga Marie",
    "Kabongo Georges", "Mwenze Angèle", "Nkulu Vincent", "Kazadi Odette",
    "Banza Alphonse", "Mutombo Chantal",
]


def get_or_create(model, defaults=None, **lookup):
    instance = model.query.filter_by(**lookup).first()
    if instance:
        return instance, False
    params = dict(lookup)
    params.update(defaults or {})
    instance = model(**params)
    db.session.add(instance)
    db.session.flush()
    return instance, True


def create_user(email, password, school, is_demo=True):
    user = User.query.filter_by(email=email).first()
    if user:
        return user
    user = User(email=email, school_id=school.id, is_demo=is_demo)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user


def assign_role(user, role):
    if role not in user.roles:
        user.roles.append(role)


def run():
    app = create_app()
    with app.app_context():
        school, _ = get_or_create(
            School,
            name="CS Jérusalem Lubumbashi",
            defaults={
                "city": app.config["SCHOOL_CITY"],
                "province": app.config["SCHOOL_PROVINCE"],
                "country": app.config["SCHOOL_COUNTRY"],
                "currency_default": app.config["SCHOOL_CURRENCY_DEFAULT"],
            },
        )

        school_year, _ = get_or_create(
            SchoolYear,
            school_id=school.id,
            label="2025-2026",
            defaults={
                "start_date": datetime.date(2025, 9, 1),
                "end_date": datetime.date(2026, 7, 3),
                "is_current": True,
            },
        )

        # --- Rôles & permissions ---
        roles_by_code = {}
        for code, label in constants.ROLE_LABELS.items():
            role, _ = get_or_create(Role, code=code, defaults={"label": label})
            roles_by_code[code] = role

        permissions_by_code = {}
        for code, label in constants.PERMISSION_LABELS.items():
            permission, _ = get_or_create(Permission, code=code, defaults={"label": label})
            permissions_by_code[code] = permission

        # SUPER_ADMIN reçoit automatiquement toutes les permissions.
        for permission in permissions_by_code.values():
            exists = RolePermission.query.filter_by(
                role_id=roles_by_code[constants.SUPER_ADMIN].id, permission_id=permission.id
            ).first()
            if not exists:
                db.session.add(
                    RolePermission(role_id=roles_by_code[constants.SUPER_ADMIN].id, permission_id=permission.id)
                )

        for role_code, permission_codes in constants.ROLE_DEFAULT_PERMISSIONS.items():
            for permission_code in permission_codes:
                exists = RolePermission.query.filter_by(
                    role_id=roles_by_code[role_code].id,
                    permission_id=permissions_by_code[permission_code].id,
                ).first()
                if not exists:
                    db.session.add(
                        RolePermission(
                            role_id=roles_by_code[role_code].id,
                            permission_id=permissions_by_code[permission_code].id,
                        )
                    )

        db.session.commit()

        # --- Compte Super Admin réel (pas démo) ---
        admin_user = create_user(app.config["ADMIN_EMAIL"], app.config["ADMIN_MOT_DE_PASSE"], school, is_demo=False)
        assign_role(admin_user, roles_by_code[constants.SUPER_ADMIN])
        get_or_create(
            StaffProfile,
            user_id=admin_user.id,
            defaults={"school_id": school.id, "nom": "Administrateur Système", "fonction": "Super Admin"},
        )

        # --- Personnel de direction (démo) ---
        prefet_user = create_user("prefet.demo@csjerusalem.cd", DEMO_PASSWORD, school)
        assign_role(prefet_user, roles_by_code[constants.PREFET])
        get_or_create(
            StaffProfile,
            user_id=prefet_user.id,
            defaults={"school_id": school.id, "nom": PREFET_NOM, "fonction": "Préfet des Études", "is_demo": True},
        )

        directeur_etudes_user = create_user("directeur.etudes.demo@csjerusalem.cd", DEMO_PASSWORD, school)
        assign_role(directeur_etudes_user, roles_by_code[constants.DIRECTEUR_ETUDES])
        get_or_create(
            StaffProfile,
            user_id=directeur_etudes_user.id,
            defaults={
                "school_id": school.id,
                "nom": DIRECTEUR_ETUDES_NOM,
                "fonction": "Directeur des Études",
                "is_demo": True,
            },
        )

        directeur_discipline_user = create_user("directeur.discipline.demo@csjerusalem.cd", DEMO_PASSWORD, school)
        assign_role(directeur_discipline_user, roles_by_code[constants.DIRECTEUR_DISCIPLINE])
        get_or_create(
            StaffProfile,
            user_id=directeur_discipline_user.id,
            defaults={
                "school_id": school.id,
                "nom": DIRECTEUR_DISCIPLINE_NOM,
                "fonction": "Directeur de Discipline",
                "is_demo": True,
            },
        )

        # --- Enseignants (démo) ---
        teacher_profiles = []
        for i, nom in enumerate(TEACHER_NAMES, start=1):
            email = f"enseignant{i}.demo@csjerusalem.cd"
            user = create_user(email, DEMO_PASSWORD, school)
            assign_role(user, roles_by_code[constants.ENSEIGNANT])
            profile, _ = get_or_create(
                TeacherProfile,
                user_id=user.id,
                defaults={"school_id": school.id, "nom": nom, "is_demo": True},
            )
            teacher_profiles.append(profile)

        # --- Comptables (démo) ---
        comptable_users = []
        for i, nom in enumerate(COMPTABLE_NAMES, start=1):
            email = f"comptable{i}.demo@csjerusalem.cd"
            user = create_user(email, DEMO_PASSWORD, school)
            assign_role(user, roles_by_code[constants.COMPTABLE])
            get_or_create(
                StaffProfile,
                user_id=user.id,
                defaults={"school_id": school.id, "nom": nom, "fonction": "Comptable", "is_demo": True},
            )
            comptable_users.append(user)

        # --- Matières ---
        subject_names = [
            ("Mathématiques", 4),
            ("Français", 4),
            ("Anglais", 2),
            ("Sciences", 3),
            ("Histoire-Géographie", 2),
            ("Éducation chrétienne", 1),
        ]
        subjects_by_name = {}
        for name, coeff in subject_names:
            subject, _ = get_or_create(Subject, school_id=school.id, name=name, defaults={"default_coefficient": coeff})
            subjects_by_name[name] = subject

        # --- Classes ---
        classe_defs = ["6e Sciences A", "6e Sciences B", "1re Humanités"]
        classes = []
        for name in classe_defs:
            level = name.split(" ")[0]
            classe, _ = get_or_create(
                Classe,
                school_id=school.id,
                school_year_id=school_year.id,
                name=name,
                defaults={"level": level, "section": "Sciences" if "Sciences" in name else "Humanités"},
            )
            classes.append(classe)

        # --- Élèves + inscriptions ---
        student_profiles = []
        for i in range(20):
            prenom = STUDENT_FIRST_NAMES[i]
            nom = STUDENT_LAST_NAMES[i]
            matricule = f"CSJ-2026-{i + 1:04d}"
            profile = StudentProfile.query.filter_by(matricule=matricule).first()
            if not profile:
                profile = StudentProfile(
                    school_id=school.id,
                    matricule=matricule,
                    nom=nom,
                    prenom=prenom,
                    sexe="M" if i % 2 == 0 else "F",
                    date_naissance=datetime.date(2011, (i % 12) + 1, 10),
                    nationalite="Congolaise",
                    is_demo=True,
                )
                db.session.add(profile)
                db.session.flush()
            student_profiles.append(profile)

            classe = classes[i % len(classes)]
            get_or_create(
                Enrollment,
                student_profile_id=profile.id,
                school_year_id=school_year.id,
                defaults={"classe_id": classe.id, "status": Enrollment.STATUS_ACTIF},
            )

        classe_students = {c.id: [] for c in classes}
        for i, profile in enumerate(student_profiles):
            classe_students[classes[i % len(classes)].id].append(profile)

        # --- Évaluations & notes (démo, 1er trimestre) ---
        assessment_type_defs = [("DEVOIR", "Devoir"), ("EXAMEN", "Examen")]
        assessment_types = []
        for code, label in assessment_type_defs:
            at, _ = get_or_create(AssessmentType, school_id=school.id, code=code, defaults={"label": label})
            assessment_types.append(at)

        graded_subject_names = ["Mathématiques", "Français", "Anglais"]
        term = constants.TERM_T1

        for classe in classes:
            students_in_classe = classe_students[classe.id]
            for subject_index, subject_name in enumerate(graded_subject_names):
                subject = subjects_by_name[subject_name]
                teacher = teacher_profiles[(classe.id + subject_index) % len(teacher_profiles)]

                for type_index, assessment_type in enumerate(assessment_types):
                    coefficient = 1 if assessment_type.code == "DEVOIR" else 2
                    assessment, created = get_or_create(
                        Assessment,
                        subject_id=subject.id,
                        classe_id=classe.id,
                        assessment_type_id=assessment_type.id,
                        school_year_id=school_year.id,
                        term=term,
                        defaults={
                            "teacher_profile_id": teacher.id,
                            "date": datetime.date(2025, 10, 6 + type_index * 14),
                            "coefficient": coefficient,
                            "max_score": 20,
                        },
                    )
                    if not created:
                        continue
                    for student in students_in_classe:
                        score = 8 + ((student.id * 7 + assessment.id * 3 + type_index) % 12)
                        db.session.add(
                            Grade(
                                assessment_id=assessment.id,
                                student_profile_id=student.id,
                                score=score,
                                entered_by_user_id=teacher.user_id,
                                entered_at=utcnow(),
                            )
                        )
        db.session.commit()

        # --- Salles + emploi du temps (démo) : mêmes couples classe/matière/enseignant que
        # les évaluations ci-dessus, pour que l'affectation formelle (Schedule) corresponde
        # à ce qui a déjà été noté — sinon un enseignant démo perdrait l'accès à ses propres
        # évaluations une fois le scoping par affectation activé. ---
        room_defs = ["Salle 101", "Salle 102", "Laboratoire"]
        rooms = []
        for name in room_defs:
            room, _ = get_or_create(Room, school_id=school.id, name=name, defaults={"capacity": 40})
            rooms.append(room)

        for classe_index, classe in enumerate(classes):
            for subject_index, subject_name in enumerate(graded_subject_names):
                subject = subjects_by_name[subject_name]
                teacher = teacher_profiles[(classe.id + subject_index) % len(teacher_profiles)]
                room = rooms[classe_index % len(rooms)]
                start_time = datetime.time(8 + subject_index, 0)
                end_time = datetime.time(9 + subject_index, 0)

                exists = Schedule.query.filter_by(
                    school_year_id=school_year.id, classe_id=classe.id, subject_id=subject.id
                ).first()
                if exists:
                    continue

                day = None
                for candidate_day in Schedule.DAY_CHOICES:
                    conflicts = check_conflicts(
                        school_year_id=school_year.id,
                        classe_id=classe.id,
                        teacher_profile_id=teacher.id,
                        room_id=room.id,
                        day=candidate_day,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    if not conflicts:
                        day = candidate_day
                        break

                if day:
                    db.session.add(
                        Schedule(
                            school_year_id=school_year.id,
                            classe_id=classe.id,
                            subject_id=subject.id,
                            teacher_profile_id=teacher.id,
                            room_id=room.id,
                            day=day,
                            start_time=start_time,
                            end_time=end_time,
                        )
                    )
                    db.session.flush()
        db.session.commit()

        # --- Bibliothèque numérique (démo) : un support de cours et un devoir, sur une
        # combinaison classe/matière/enseignant réellement affectée dans l'emploi du temps
        # (via Schedule) ci-dessus — sinon l'enseignant démo n'y aurait pas accès une fois le
        # scoping par affectation appliqué. ---
        first_schedule_entry = Schedule.query.filter_by(school_year_id=school_year.id, classe_id=classes[0].id).first()
        if first_schedule_entry:
            material, _ = get_or_create(
                CourseMaterial,
                classe_id=first_schedule_entry.classe_id,
                subject_id=first_schedule_entry.subject_id,
                title="Introduction — chapitre 1",
                defaults={
                    "school_year_id": school_year.id,
                    "teacher_profile_id": first_schedule_entry.teacher_profile_id,
                    "description": "Support de cours du premier chapitre, à lire avant le prochain cours.",
                    "category": CourseMaterial.CATEGORY_SUPPORT,
                    "is_demo": True,
                },
            )
            homework, _ = get_or_create(
                Homework,
                classe_id=first_schedule_entry.classe_id,
                subject_id=first_schedule_entry.subject_id,
                title="Exercices série 1",
                defaults={
                    "school_year_id": school_year.id,
                    "teacher_profile_id": first_schedule_entry.teacher_profile_id,
                    "instructions": "Faire les exercices 1 à 5 de la page 12.",
                    "due_date": datetime.date(2026, 9, 1),
                    "is_demo": True,
                },
            )
            db.session.commit()

        # --- Un bulletin déjà généré (démo, preuve du pipeline PDF) ---
        first_student = classe_students[classes[0].id][0]
        report_card, _ = get_or_create(
            ReportCard,
            student_profile_id=first_student.id,
            school_year_id=school_year.id,
            term=term,
            defaults={"generated_at": utcnow(), "status": ReportCard.STATUS_GENERATED},
        )
        db.session.flush()
        subject_averages = student_subject_averages(first_student.id, school_year.id, term)
        overall = student_overall_average(first_student.id, school_year.id, term)
        report_card.pdf_path = generate_and_save_bulletin(
            report_card, first_student, school, school_year, subject_averages, overall
        )
        db.session.commit()

        # --- Présences (démo) : quelques jours récents, y compris aujourd'hui, pour que les
        # tableaux de bord (Préfet, Discipline) affichent des chiffres dès la première visite. ---
        today = datetime.date.today()
        attendance_dates = [today - datetime.timedelta(days=offset) for offset in range(5)]

        first_absence_marked_justified = False
        for classe in classes:
            teacher = teacher_profiles[classe.id % len(teacher_profiles)]
            for date_index, att_date in enumerate(attendance_dates):
                for student in classe_students[classe.id]:
                    exists = Attendance.query.filter_by(
                        student_profile_id=student.id, classe_id=classe.id, subject_id=None, date=att_date
                    ).first()
                    if exists:
                        continue

                    roll = (student.id + date_index) % 10
                    if roll == 0:
                        status = Attendance.STATUS_ABSENT
                        arrival_time = None
                    elif roll == 1:
                        status = Attendance.STATUS_RETARD
                        arrival_time = datetime.time(8, 15)
                    else:
                        status = Attendance.STATUS_PRESENT
                        arrival_time = None

                    justified = False
                    if status == Attendance.STATUS_ABSENT and not first_absence_marked_justified:
                        justified = True
                        first_absence_marked_justified = True

                    db.session.add(
                        Attendance(
                            student_profile_id=student.id,
                            classe_id=classe.id,
                            subject_id=None,
                            school_year_id=school_year.id,
                            date=att_date,
                            status=status,
                            arrival_time=arrival_time,
                            justified=justified,
                            recorded_by_user_id=teacher.user_id,
                        )
                    )
        db.session.commit()

        # --- Parents (démo), liés à ~2 élèves chacun ---
        for i, nom in enumerate(PARENT_NAMES):
            email = f"parent{i + 1}.demo@csjerusalem.cd"
            user = create_user(email, DEMO_PASSWORD, school)
            assign_role(user, roles_by_code[constants.PARENT])
            profile, _ = get_or_create(
                ParentProfile,
                user_id=user.id,
                defaults={"school_id": school.id, "nom": nom, "is_demo": True},
            )
            children = student_profiles[i * 2 : i * 2 + 2]
            for child in children:
                link = ParentStudent.query.filter_by(
                    parent_profile_id=profile.id, student_profile_id=child.id
                ).first()
                if not link:
                    db.session.add(
                        ParentStudent(parent_profile_id=profile.id, student_profile_id=child.id, relation="Parent")
                    )
        db.session.commit()

        # --- Notifications pour le bulletin déjà généré plus haut (élève + parents — les
        # parents ne sont liés qu'à partir d'ici, d'où ce placement après leur création). ---
        first_student_parents = list(first_student.parents)
        already_notified = bool(
            first_student_parents
            and Notification.query.filter_by(
                user_id=first_student_parents[0].user_id, type=Notification.TYPE_RESULTAT
            ).first()
        )
        if not already_notified:
            if first_student.user:
                notify(
                    first_student.user,
                    Notification.TYPE_RESULTAT,
                    title=f"Bulletin disponible — {constants.TERM_LABELS.get(term, term)}",
                    body=f"Moyenne générale : {overall:.2f}/20." if overall is not None else None,
                )
            for parent in first_student_parents:
                notify(
                    parent.user,
                    Notification.TYPE_RESULTAT,
                    title=f"Bulletin disponible — {first_student.full_name} ({constants.TERM_LABELS.get(term, term)})",
                    body=f"Moyenne générale : {overall:.2f}/20." if overall is not None else None,
                )
            db.session.commit()

        # --- Discipline (démo) : quelques incidents avec mesures, et des convocations à
        # différents statuts, pour montrer le cycle complet (créée → ... → confirmée). ---
        incident_defs = [
            {
                "student": student_profiles[0],
                "date": datetime.date(2025, 10, 10),
                "severity": DisciplinaryIncident.SEVERITY_LOW,
                "description": "Bavardage répété en classe malgré plusieurs avertissements oraux.",
                "action_type": DisciplinaryAction.TYPE_AVERTISSEMENT,
            },
            {
                "student": student_profiles[8],
                "date": datetime.date(2025, 11, 5),
                "severity": DisciplinaryIncident.SEVERITY_MEDIUM,
                "description": "Bagarre avec un camarade de classe pendant la récréation.",
                "action_type": DisciplinaryAction.TYPE_SANCTION,
            },
        ]

        for definition in incident_defs:
            student = definition["student"]
            existing_incident = DisciplinaryIncident.query.filter_by(
                student_profile_id=student.id, date=definition["date"]
            ).first()
            if existing_incident:
                continue

            incident = DisciplinaryIncident(
                school_year_id=school_year.id,
                student_profile_id=student.id,
                reported_by_user_id=directeur_discipline_user.id,
                date=definition["date"],
                description=definition["description"],
                severity=definition["severity"],
            )
            db.session.add(incident)
            db.session.flush()

            db.session.add(
                DisciplinaryAction(
                    incident_id=incident.id,
                    type=definition["action_type"],
                    decided_by_user_id=directeur_discipline_user.id,
                    date=definition["date"],
                    details="Mesure appliquée après entretien avec l'élève.",
                )
            )

        convocation_defs = [
            {
                "student": student_profiles[0],
                "motif": "Comportement en classe",
                "date": datetime.date(2025, 10, 15),
                "heure": datetime.time(14, 0),
                "status": Convocation.STATUS_ENVOYEE,
            },
            {
                "student": student_profiles[8],
                "motif": "Suite à l'incident du 5 novembre",
                "date": datetime.date(2025, 11, 10),
                "heure": datetime.time(10, 0),
                "status": Convocation.STATUS_CONFIRMEE,
            },
        ]

        for definition in convocation_defs:
            student = definition["student"]
            parents = list(student.parents)
            if not parents:
                continue
            existing_convocation = Convocation.query.filter_by(
                student_profile_id=student.id, date=definition["date"]
            ).first()
            if existing_convocation:
                continue

            convocation = Convocation(
                student_profile_id=student.id,
                parent_profile_id=parents[0].id,
                created_by_user_id=directeur_discipline_user.id,
                motif=definition["motif"],
                date=definition["date"],
                heure=definition["heure"],
                lieu="Bureau de la Discipline",
                status=definition["status"],
            )
            db.session.add(convocation)

            if definition["status"] != Convocation.STATUS_CREEE:
                notify(
                    parents[0].user,
                    Notification.TYPE_CONVOCATION,
                    title=f"Convocation — {student.full_name}",
                    body=f"{convocation.motif}, le {convocation.date.strftime('%d/%m/%Y')} à {convocation.heure.strftime('%H:%M')}.",
                )

        db.session.commit()

        # --- Finance : frais scolaires, paiements et reçus (démo) ---
        fee_type_defs = [
            ("FRAIS_SCOLAIRE", "Frais scolaires 2025-2026", 150000),
            ("INSCRIPTION", "Frais d'inscription", 25000),
        ]
        fee_types = []
        for code, label, amount in fee_type_defs:
            fee_type, _ = get_or_create(
                FeeType,
                school_id=school.id,
                school_year_id=school_year.id,
                code=code,
                defaults={"label": label, "default_amount": amount, "currency": school.currency_default},
            )
            fee_types.append(fee_type)

        fees_by_student = {}
        for profile in student_profiles:
            fees_by_student[profile.id] = []
            for fee_type in fee_types:
                fee, _ = get_or_create(
                    Fee,
                    student_profile_id=profile.id,
                    fee_type_id=fee_type.id,
                    school_year_id=school_year.id,
                    defaults={"amount_due": fee_type.default_amount},
                )
                fees_by_student[profile.id].append(fee)

        comptable_user = comptable_users[0]
        payment_date = datetime.date(2025, 9, 15)

        def record_demo_payment(fee, amount):
            existing = Payment.query.filter_by(fee_id=fee.id, amount=amount, payment_date=payment_date).first()
            if existing:
                return
            payment = Payment(
                student_profile_id=fee.student_profile_id,
                fee_id=fee.id,
                amount=amount,
                currency=fee.fee_type.currency,
                method=Payment.METHOD_ESPECES,
                recorded_by_user_id=comptable_user.id,
                payment_date=payment_date,
            )
            db.session.add(payment)
            db.session.flush()
            receipt = Receipt(payment_id=payment.id, number=next_document_number(Receipt, payment_date.year))
            db.session.add(receipt)
            db.session.flush()
            generate_and_save_receipt(payment, receipt, school)

            student = db.session.get(StudentProfile, fee.student_profile_id)
            for parent in student.parents:
                notify(
                    parent.user,
                    Notification.TYPE_PAIEMENT,
                    title=f"Paiement enregistré — {student.full_name}",
                    body=f"{payment.amount:.2f} {payment.currency} pour {fee.fee_type.label}. Reçu {receipt.number}.",
                )

        # 5 élèves à jour (les deux frais payés intégralement)
        for profile in student_profiles[0:5]:
            for fee in fees_by_student[profile.id]:
                record_demo_payment(fee, fee.amount_due)

        # 5 élèves partiellement payés (frais scolaires payé à moitié, inscription impayée)
        for profile in student_profiles[5:10]:
            scolaire_fee = fees_by_student[profile.id][0]
            record_demo_payment(scolaire_fee, scolaire_fee.amount_due / 2)

        # Les 10 restants n'ont aucun paiement enregistré (élèves en retard).

        db.session.commit()

        # --- Dépenses (démo) ---
        expense_defs = [
            ("Fournitures scolaires", 45000, datetime.date(2025, 9, 5)),
            ("Entretien des locaux", 60000, datetime.date(2025, 9, 20)),
        ]
        for category, amount, date in expense_defs:
            exists = Expense.query.filter_by(
                school_id=school.id, category=category, amount=amount, expense_date=date
            ).first()
            if not exists:
                db.session.add(
                    Expense(
                        school_id=school.id,
                        school_year_id=school_year.id,
                        category=category,
                        amount=amount,
                        currency=school.currency_default,
                        expense_date=date,
                        recorded_by_user_id=comptable_user.id,
                    )
                )
        db.session.commit()

        # --- Préinscriptions (démo) : un dossier par statut, pour montrer tout le cycle
        # d'instruction (y compris un dossier accepté qui a réellement créé un élève). ---
        application_defs = [
            {
                "nom": "Kalubi", "prenom": "Emmanuel", "sexe": "M",
                "parent_nom": "Kalubi Ferdinand", "parent_telephone": "+243810000001",
                "status": Application.STATUS_SOUMIS,
            },
            {
                "nom": "Ntambwe", "prenom": "Grace", "sexe": "F",
                "parent_nom": "Ntambwe Chantal", "parent_telephone": "+243810000002",
                "status": Application.STATUS_EN_EXAMEN,
            },
            {
                "nom": "Kasongo", "prenom": "Divine", "sexe": "F",
                "parent_nom": "Kasongo Robert", "parent_telephone": "+243810000003",
                "status": Application.STATUS_INCOMPLET,
            },
            {
                "nom": "Mbayo", "prenom": "Joseph", "sexe": "M",
                "parent_nom": "Mbayo Alphonse", "parent_telephone": "+243810000004",
                "status": Application.STATUS_ACCEPTE,
            },
            {
                "nom": "Kalonji", "prenom": "Sarah", "sexe": "F",
                "parent_nom": "Kalonji Odette", "parent_telephone": "+243810000005",
                "status": Application.STATUS_REFUSE,
            },
        ]

        for i, definition in enumerate(application_defs):
            existing_application = Application.query.filter_by(
                nom=definition["nom"], prenom=definition["prenom"], is_demo=True
            ).first()
            if existing_application:
                continue

            application = Application(
                school_id=school.id,
                number=next_document_number(Application, 2026),
                nom=definition["nom"],
                prenom=definition["prenom"],
                sexe=definition["sexe"],
                date_naissance=datetime.date(2012, (i % 12) + 1, 15),
                nationalite="Congolaise",
                classe_demandee_id=classes[i % len(classes)].id,
                parent_nom=definition["parent_nom"],
                parent_telephone=definition["parent_telephone"],
                parent_relation="Parent",
                status=Application.STATUS_SOUMIS,
                is_demo=True,
            )
            db.session.add(application)
            db.session.flush()

            target_status = definition["status"]
            if target_status == Application.STATUS_ACCEPTE:
                accept_application(application, prefet_user, comment="Dossier complet, admis à l'essai.")
            elif target_status == Application.STATUS_REFUSE:
                application.status = Application.STATUS_REFUSE
                application.decision_comment = "Aucune place disponible dans la classe demandée."
                application.decided_at = utcnow()
                application.decided_by_user_id = prefet_user.id
            elif target_status in (Application.STATUS_EN_EXAMEN, Application.STATUS_INCOMPLET):
                application.status = target_status

        db.session.commit()

        # --- Actualités & Événements (démo) : deux publiées, une en brouillon (pour vérifier
        # qu'elle reste invisible sur le site public), et deux événements à venir. ---
        announcement_defs = [
            {
                "title": "Rentrée scolaire 2025-2026",
                "body": "La rentrée des classes aura lieu le 2 septembre 2025. Les frais d'inscription "
                        "peuvent être réglés au secrétariat ou en ligne via le portail parent.",
                "category": Announcement.CATEGORY_GENERAL,
                "status": Announcement.STATUS_PUBLIE,
                "image_filename": "IMG_20240902_083613_801.jpg",
            },
            {
                "title": "Résultats du premier trimestre disponibles",
                "body": "Les bulletins du premier trimestre sont désormais consultables depuis l'espace "
                        "Élève et l'espace Parent du portail numérique.",
                "category": Announcement.CATEGORY_ACADEMIQUE,
                "status": Announcement.STATUS_PUBLIE,
                "image_filename": "IMG_20240130_144020_943.jpg",
            },
            {
                "title": "Préparatifs de la fête de fin d'année (brouillon)",
                "body": "Note interne en préparation, ne pas publier avant validation de la Direction.",
                "category": Announcement.CATEGORY_EVENEMENT,
                "status": Announcement.STATUS_BROUILLON,
                "image_filename": None,
            },
        ]
        for definition in announcement_defs:
            existing = Announcement.query.filter_by(title=definition["title"], is_demo=True).first()
            if existing:
                announcement = existing
            else:
                announcement = Announcement(
                    school_id=school.id,
                    title=definition["title"],
                    body=definition["body"],
                    category=definition["category"],
                    status=definition["status"],
                    author_id=prefet_user.id,
                    published_at=utcnow() if definition["status"] == Announcement.STATUS_PUBLIE else None,
                    is_demo=True,
                )
                db.session.add(announcement)
                db.session.flush()

            if definition["image_filename"]:
                attach_photo_if_available("Announcement", announcement.id, definition["image_filename"])

        event_defs = [
            {
                "title": "Portes ouvertes",
                "description": "Présentation de l'établissement aux futures familles.",
                "category": Event.CATEGORY_AUTRE,
                "date": datetime.date(2026, 9, 15),
                "image_filename": "IMG_20250130_101819_112.jpg",
            },
            {
                "title": "Culte de rentrée",
                "description": "Culte œcuménique d'ouverture de l'année scolaire.",
                "category": Event.CATEGORY_RELIGIEUX,
                "date": datetime.date(2026, 9, 3),
                "image_filename": "IMG_20241219_104006_661.jpg",
            },
        ]
        for definition in event_defs:
            existing = Event.query.filter_by(title=definition["title"], is_demo=True).first()
            if existing:
                event = existing
            else:
                event = Event(
                    school_id=school.id,
                    title=definition["title"],
                    description=definition["description"],
                    category=definition["category"],
                    date=definition["date"],
                    created_by_user_id=prefet_user.id,
                    is_demo=True,
                )
                db.session.add(event)
                db.session.flush()

            if definition["image_filename"]:
                attach_photo_if_available("Event", event.id, definition["image_filename"])

        db.session.commit()

        # --- Comptes de connexion pour 3 élèves démo (proof of scoping élève) ---
        for profile in student_profiles[:3]:
            email = f"eleve.{profile.matricule.lower()}@csjerusalem.cd"
            user = create_user(email, DEMO_PASSWORD, school)
            assign_role(user, roles_by_code[constants.ELEVE])
            profile.user_id = user.id

        db.session.commit()

        print("Données démo créées avec succès.")
        print(f"Mot de passe démo commun : {DEMO_PASSWORD}")
        print(f"Super Admin réel : {app.config['ADMIN_EMAIL']} / (mot de passe défini dans .env)")
        print("Comptes démo : prefet.demo@csjerusalem.cd, directeur.etudes.demo@csjerusalem.cd, "
              "directeur.discipline.demo@csjerusalem.cd, enseignant1..5.demo@csjerusalem.cd, "
              "comptable1..2.demo@csjerusalem.cd, parent1..10.demo@csjerusalem.cd, "
              "eleve.csj-2026-0001@csjerusalem.cd (+ 2 autres)")


if __name__ == "__main__":
    run()
