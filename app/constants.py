"""Catalogue central des rôles et permissions.

Ajouter un rôle ou une permission ici (puis re-seed) suffit à les rendre disponibles
dans tout le système — aucun autre fichier ne doit contenir de liste de rôles codée en dur.
"""

# Rôles (Role.code)
SUPER_ADMIN = "SUPER_ADMIN"
PREFET = "PREFET"
DIRECTEUR_ETUDES = "DIRECTEUR_ETUDES"
DIRECTEUR_DISCIPLINE = "DIRECTEUR_DISCIPLINE"
ENSEIGNANT = "ENSEIGNANT"
COMPTABLE = "COMPTABLE"
PARENT = "PARENT"
ELEVE = "ELEVE"

ROLE_LABELS = {
    SUPER_ADMIN: "Super Administrateur",
    PREFET: "Préfet des Études",
    DIRECTEUR_ETUDES: "Directeur des Études",
    DIRECTEUR_DISCIPLINE: "Directeur de Discipline",
    ENSEIGNANT: "Enseignant",
    COMPTABLE: "Comptable",
    PARENT: "Parent / Tuteur",
    ELEVE: "Élève",
}

ALL_ROLES = list(ROLE_LABELS.keys())

# Permissions (Permission.code) — catalogue P0.
# D'autres permissions plus fines (ex: grades.edit_own_class, finance.manage) seront
# ajoutées au fil des modules suivants ; le mécanisme de vérification ne change pas.
DASHBOARD_PREFET = "dashboard.view_prefet"
DASHBOARD_DIRECTION_ETUDES = "dashboard.view_direction_etudes"
DASHBOARD_DISCIPLINE = "dashboard.view_discipline"
DASHBOARD_ENSEIGNANT = "dashboard.view_enseignant"
DASHBOARD_COMPTABLE = "dashboard.view_comptable"
DASHBOARD_PARENT = "dashboard.view_parent"
DASHBOARD_ELEVE = "dashboard.view_eleve"
ADMIN_MANAGE_USERS = "admin.manage_users"
ADMIN_MANAGE_SETTINGS = "admin.manage_settings"
ADMIN_VIEW_AUDIT_LOG = "admin.view_audit_log"

# Le Comptable gère les opérations financières (frais, paiements, reçus, dépenses).
# Le Préfet ne reçoit QUE la vue globale en lecture seule (brief section 8 : "consulter...
# sans pouvoir modifier les opérations comptables sauf permission spécifique").
FINANCE_MANAGE = "finance.manage"
FINANCE_VIEW_GLOBAL = "finance.view_global"

# L'Enseignant gère ses propres évaluations/notes (scoping sur Assessment.teacher_profile_id,
# voir app/models/grading.py). La Direction des Études et le Préfet supervisent en lecture
# seule (brief : "supervision des notes" — l'encodage reste la responsabilité de l'enseignant).
GRADES_MANAGE_OWN = "grades.manage_own"
GRADES_VIEW_ALL = "grades.view_all"

# Génération de bulletins : action d'écriture, distincte de GRADES_VIEW_ALL pour que le
# Préfet (lecture seule) ne puisse jamais déclencher une génération malgré son accès à la
# supervision des notes.
BULLETINS_GENERATE = "bulletins.generate"

# Présence : l'Enseignant prend l'appel (scoping sur Attendance.recorded_by_user_id, même
# convention que pour les notes). Le Directeur de Discipline consulte tout ET justifie les
# absences/retards (action d'écriture distincte de la simple consultation) ; le Préfet ne
# reçoit que la consultation, pour la même raison que pour les finances.
ATTENDANCE_RECORD = "attendance.record"
ATTENDANCE_VIEW_ALL = "attendance.view_all"
ATTENDANCE_JUSTIFY = "attendance.justify"

# Emploi du temps : la Direction des Études construit les horaires (avec détection de
# conflits, voir app/services/schedule.py) ; le Préfet consulte, même logique que finance et
# notes. Une fois peuplé, Schedule devient aussi la source de vérité de l'affectation
# enseignant↔classe utilisée pour restreindre les modules Notes et Présence.
SCHEDULE_MANAGE = "schedule.manage"
SCHEDULE_VIEW_ALL = "schedule.view_all"

# Préinscription : la soumission est publique (aucune permission — n'importe quel visiteur
# peut déposer un dossier). Le Préfet instruit les dossiers (statut, acceptation) — rattaché
# à la supervision globale de l'établissement (brief section 8), pas à la Direction des
# Études qui ne gère que la structure académique une fois l'élève inscrit.
APPLICATIONS_MANAGE = "applications.manage"

# Discipline : les informations disciplinaires sont strictement protégées (brief section 11)
# — seuls le Directeur de Discipline (gestion complète) et le Préfet (supervision, lecture
# seule) y accèdent. Aucun autre rôle, y compris Direction des Études, n'a de permission
# discipline par défaut.
DISCIPLINE_MANAGE = "discipline.manage"
DISCIPLINE_VIEW_ALL = "discipline.view_all"

# Site public : actualités et événements, rattachés à la supervision globale de
# l'établissement (même logique que les préinscriptions) plutôt qu'à un rôle communication
# dédié, qui n'existe pas dans le brief.
CONTENT_MANAGE = "content.manage"

# Bibliothèque numérique : l'Enseignant dépose supports de cours et devoirs pour ses propres
# classes affectées (même scoping que les notes/présences, via Schedule). La Direction des
# Études supervise en lecture seule, jamais d'écriture — cohérent avec sa supervision des
# notes. Élève/Parent consultent via leur permission de tableau de bord existante
# (DASHBOARD_ELEVE/DASHBOARD_PARENT), pas de permission dédiée : ils n'ont accès qu'à leur
# propre classe, imposé par le scoping de la route, pas par une permission séparée.
LIBRARY_MANAGE_OWN = "library.manage_own"
LIBRARY_VIEW_ALL = "library.view_all"

# Rapports avancés : agrégats transversaux (présence, finance, académique) réservés au Préfet,
# qui a déjà la vue globale sur chacun de ces domaines pris séparément — ce n'est qu'une
# consolidation, pas un nouveau domaine de données.
REPORTS_VIEW = "reports.view"

TERM_T1 = "T1"
TERM_T2 = "T2"
TERM_T3 = "T3"
TERM_LABELS = {TERM_T1: "1er trimestre", TERM_T2: "2e trimestre", TERM_T3: "3e trimestre"}
TERMS = list(TERM_LABELS.keys())

PERMISSION_LABELS = {
    DASHBOARD_PREFET: "Accéder au tableau de bord Préfet",
    DASHBOARD_DIRECTION_ETUDES: "Accéder au tableau de bord Direction des Études",
    DASHBOARD_DISCIPLINE: "Accéder au tableau de bord Discipline",
    DASHBOARD_ENSEIGNANT: "Accéder au tableau de bord Enseignant",
    DASHBOARD_COMPTABLE: "Accéder au tableau de bord Comptable",
    DASHBOARD_PARENT: "Accéder au tableau de bord Parent",
    DASHBOARD_ELEVE: "Accéder au tableau de bord Élève",
    ADMIN_MANAGE_USERS: "Gérer les utilisateurs et les rôles",
    ADMIN_MANAGE_SETTINGS: "Gérer les paramètres de l'établissement",
    ADMIN_VIEW_AUDIT_LOG: "Consulter le journal d'audit (actions sensibles de tous les comptes)",
    FINANCE_MANAGE: "Gérer les frais, paiements, reçus et dépenses",
    FINANCE_VIEW_GLOBAL: "Consulter la situation financière globale (lecture seule)",
    GRADES_MANAGE_OWN: "Créer des évaluations et encoder des notes (classes affectées)",
    GRADES_VIEW_ALL: "Consulter toutes les évaluations, notes et moyennes (lecture seule)",
    BULLETINS_GENERATE: "Générer les bulletins PDF des élèves",
    ATTENDANCE_RECORD: "Faire l'appel (classes prises en charge)",
    ATTENDANCE_VIEW_ALL: "Consulter les présences/absences/retards (lecture seule)",
    ATTENDANCE_JUSTIFY: "Justifier une absence ou un retard",
    SCHEDULE_MANAGE: "Créer et modifier l'emploi du temps",
    SCHEDULE_VIEW_ALL: "Consulter l'emploi du temps global (lecture seule)",
    APPLICATIONS_MANAGE: "Instruire les dossiers de préinscription",
    DISCIPLINE_MANAGE: "Gérer les incidents, sanctions et convocations",
    DISCIPLINE_VIEW_ALL: "Consulter les dossiers disciplinaires (lecture seule)",
    CONTENT_MANAGE: "Gérer les actualités et événements du site public",
    LIBRARY_MANAGE_OWN: "Déposer des supports de cours et devoirs (classes affectées)",
    LIBRARY_VIEW_ALL: "Consulter la bibliothèque numérique de toutes les classes (lecture seule)",
    REPORTS_VIEW: "Consulter et exporter les rapports avancés (présence, finance, académique)",
}

ALL_PERMISSIONS = list(PERMISSION_LABELS.keys())

# Attribution par défaut des permissions à chaque rôle.
# SUPER_ADMIN reçoit automatiquement toutes les permissions (voir seed_demo.py / app/cli.py).
ROLE_DEFAULT_PERMISSIONS = {
    PREFET: [
        DASHBOARD_PREFET,
        FINANCE_VIEW_GLOBAL,
        GRADES_VIEW_ALL,
        ATTENDANCE_VIEW_ALL,
        SCHEDULE_VIEW_ALL,
        APPLICATIONS_MANAGE,
        DISCIPLINE_VIEW_ALL,
        CONTENT_MANAGE,
        LIBRARY_VIEW_ALL,
        REPORTS_VIEW,
    ],
    DIRECTEUR_ETUDES: [
        DASHBOARD_DIRECTION_ETUDES,
        GRADES_VIEW_ALL,
        BULLETINS_GENERATE,
        SCHEDULE_MANAGE,
        SCHEDULE_VIEW_ALL,
        LIBRARY_VIEW_ALL,
    ],
    DIRECTEUR_DISCIPLINE: [
        DASHBOARD_DISCIPLINE,
        ATTENDANCE_VIEW_ALL,
        ATTENDANCE_JUSTIFY,
        DISCIPLINE_MANAGE,
        DISCIPLINE_VIEW_ALL,
    ],
    ENSEIGNANT: [DASHBOARD_ENSEIGNANT, GRADES_MANAGE_OWN, ATTENDANCE_RECORD, LIBRARY_MANAGE_OWN],
    COMPTABLE: [DASHBOARD_COMPTABLE, FINANCE_MANAGE],
    PARENT: [DASHBOARD_PARENT],
    ELEVE: [DASHBOARD_ELEVE],
}

# Vers quel dashboard rediriger un utilisateur après connexion, selon son (premier) rôle.
ROLE_DASHBOARD_ENDPOINT = {
    SUPER_ADMIN: "admin.dashboard",
    PREFET: "prefet.dashboard",
    DIRECTEUR_ETUDES: "direction_etudes.dashboard",
    DIRECTEUR_DISCIPLINE: "discipline.dashboard",
    ENSEIGNANT: "enseignant.dashboard",
    COMPTABLE: "comptable.dashboard",
    PARENT: "parent.dashboard",
    ELEVE: "eleve.dashboard",
}

# Sidebar : entrées visibles par rôle, filtrées par permission réelle de l'utilisateur
# (voir app/services/permissions.py:sidebar_items_for) — jamais par un simple "if role == ...".
SIDEBAR_ITEMS = [
    {"label": "Tableau de bord", "endpoint": "prefet.dashboard", "permission": DASHBOARD_PREFET},
    {"label": "Tableau de bord", "endpoint": "direction_etudes.dashboard", "permission": DASHBOARD_DIRECTION_ETUDES},
    {"label": "Tableau de bord", "endpoint": "discipline.dashboard", "permission": DASHBOARD_DISCIPLINE},
    {"label": "Tableau de bord", "endpoint": "enseignant.dashboard", "permission": DASHBOARD_ENSEIGNANT},
    {"label": "Mes évaluations", "endpoint": "enseignant.assessments", "permission": GRADES_MANAGE_OWN},
    {"label": "Faire l'appel", "endpoint": "enseignant.attendance_form", "permission": ATTENDANCE_RECORD},
    {"label": "Mon emploi du temps", "endpoint": "enseignant.my_schedule", "permission": DASHBOARD_ENSEIGNANT},
    {"label": "Bibliothèque numérique", "endpoint": "enseignant.library", "permission": LIBRARY_MANAGE_OWN},
    {"label": "Tableau de bord", "endpoint": "comptable.dashboard", "permission": DASHBOARD_COMPTABLE},
    {"label": "Frais scolaires", "endpoint": "comptable.fee_types", "permission": FINANCE_MANAGE},
    {"label": "Élèves & Paiements", "endpoint": "comptable.students", "permission": FINANCE_MANAGE},
    {"label": "Dépenses", "endpoint": "comptable.expenses", "permission": FINANCE_MANAGE},
    {"label": "Tableau de bord", "endpoint": "parent.dashboard", "permission": DASHBOARD_PARENT},
    {"label": "Tableau de bord", "endpoint": "eleve.dashboard", "permission": DASHBOARD_ELEVE},
    {"label": "Mes notes", "endpoint": "eleve.notes", "permission": DASHBOARD_ELEVE},
    {"label": "Emploi du temps", "endpoint": "eleve.schedule", "permission": DASHBOARD_ELEVE},
    {"label": "Bibliothèque numérique", "endpoint": "eleve.library", "permission": DASHBOARD_ELEVE},
    {"label": "Finance (lecture seule)", "endpoint": "prefet.finance", "permission": FINANCE_VIEW_GLOBAL},
    {"label": "Notes & moyennes", "endpoint": "direction_etudes.grades_overview", "permission": GRADES_VIEW_ALL},
    {"label": "Présences", "endpoint": "discipline.attendance_overview", "permission": ATTENDANCE_VIEW_ALL},
    {"label": "Incidents & Sanctions", "endpoint": "discipline.incidents", "permission": DISCIPLINE_VIEW_ALL},
    {"label": "Convocations", "endpoint": "discipline.convocations", "permission": DISCIPLINE_VIEW_ALL},
    {"label": "Emploi du temps", "endpoint": "direction_etudes.schedule_list", "permission": SCHEDULE_VIEW_ALL},
    {"label": "Bibliothèque (supervision)", "endpoint": "direction_etudes.library_overview", "permission": LIBRARY_VIEW_ALL},
    {"label": "Préinscriptions", "endpoint": "prefet.applications", "permission": APPLICATIONS_MANAGE},
    {"label": "Actualités & Événements", "endpoint": "prefet.content", "permission": CONTENT_MANAGE},
    {"label": "Messages de contact", "endpoint": "prefet.contact_messages", "permission": CONTENT_MANAGE},
    {"label": "Rapports", "endpoint": "prefet.reports", "permission": REPORTS_VIEW},
    {"label": "Utilisateurs", "endpoint": "admin.users", "permission": ADMIN_MANAGE_USERS},
    {"label": "Paramètres", "endpoint": "admin.settings", "permission": ADMIN_MANAGE_SETTINGS},
    {"label": "Journal d'audit", "endpoint": "admin.audit_log", "permission": ADMIN_VIEW_AUDIT_LOG},
]
