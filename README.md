# CS Jérusalem — Portail Scolaire Numérique

Système d'Information Scolaire (SIS) pour le CS Jérusalem, école secondaire méthodiste à
Lubumbashi (Haut-Katanga, RDC). Voir `.claude/plans/` de la session de conception pour
l'architecture complète (schéma de base de données, RBAC, roadmap par étapes).

**État actuel : P0, P1 et P2 complets.** Authentification et RBAC réel (backend, jamais
seulement l'UI), 8 espaces par rôle, finance/paiements/reçus PDF, notes/bulletins PDF,
présences, emploi du temps (avec détection de conflits), préinscription publique, discipline
(incidents/sanctions/convocations), notifications (web + email réels, SMS/WhatsApp en attente
d'un fournisseur), site public élargi (actualités/événements/galerie avec carrousel photo),
bibliothèque numérique, rapports avancés exportables en PDF, administration Super Admin
(utilisateurs, paramètres, années scolaires, identité visuelle, journal d'audit réellement
persisté). Voir la section « Déploiement en production » pour la mise en ligne.

## Stack

Flask 3 + SQLAlchemy + Flask-Migrate (Alembic) + Flask-Login + Flask-WTF + Flask-Limiter.
MySQL en production (PyMySQL), SQLite par défaut en développement local si `DATABASE_URL`
n'est pas défini. Génération PDF (reçus) via xhtml2pdf — pur Python, choisi à la place de
WeasyPrint qui nécessite des bibliothèques natives (GTK/Pango) absentes par défaut sur
Windows et sur de nombreux hébergements simples.

## Module Finance (Comptable + vue Préfet)

- Le Comptable crée des **types de frais** (`/comptable/frais`) — chaque type s'applique
  automatiquement à tous les élèves actifs de l'année scolaire en cours.
- Il enregistre des **paiements** par élève (`/comptable/eleves`), ce qui génère
  automatiquement un **reçu PDF** numéroté `CSJ-<année>-XXXXX`, téléchargeable et
  régénérable à tout moment.
- Il suit les **dépenses** de l'établissement (`/comptable/depenses`).
- Le Préfet dispose d'une vue **lecture seule** de la situation financière globale
  (`/prefet/finance`) — aucune action d'écriture n'est possible depuis cette vue, y compris
  en devinant les URL du Comptable (vérifié : 403 backend, pas seulement absence de lien).

## Module Notes & Bulletins (Enseignant, Direction des Études, Élève, Parent)

- L'Enseignant crée des **évaluations** (`/enseignant/evaluations`) — la liste déroulante
  classe/matière ne propose que les combinaisons auxquelles il est réellement affecté dans
  l'emploi du temps (`app.services.schedule.teacher_affectations`). Il encode ensuite les
  notes par élève.
- Les moyennes (par matière, pondérées par coefficient d'évaluation, puis moyenne générale
  pondérée par coefficient de matière) sont calculées par un seul service partagé
  (`app/services/grades.py`) — jamais recalculées différemment selon l'écran.
- La Direction des Études supervise en **lecture seule** (`/direction-etudes/notes`) et peut
  **générer les bulletins PDF** (`bulletins.generate`) — une permission distincte de la
  supervision en lecture seule, pour que le Préfet (qui partage l'accès en lecture) ne puisse
  jamais déclencher une génération malgré son accès à la même page.
- Élève et Parent consultent leurs propres notes/bulletins uniquement (vérifié : 403 sur les
  bulletins ou dossiers d'un autre élève, y compris en devinant l'URL).

## Module Présence (Enseignant, Discipline, Préfet, Élève, Parent)

- L'Enseignant fait l'**appel** (`/enseignant/presence`) par classe/matière/date — même
  logique de scoping par affectation que les évaluations ; une tentative d'appel sur une
  classe non affectée (même en devinant l'URL) retourne 403.
- Un service partagé (`app/services/attendance.py`) résume "la journée" d'un élève quand
  plusieurs appels par matière existent le même jour (ABSENT > RETARD > PRESENT), pour que
  Préfet, Discipline, Élève et Parent voient toujours le même chiffre.
- Le Directeur de Discipline consulte les absences/retards (`/discipline/presence`) et les
  **justifie** (`attendance.justify`) — action distincte de la consultation, pour que le
  Préfet (même page, lecture seule) ne puisse jamais justifier malgré son accès en lecture
  (vérifié : 403 backend même avec un jeton CSRF valide).
- Le Préfet voit le taux de présence du jour sur son tableau de bord ; Élève et Parent voient
  leurs propres absences/retards de l'année (vérifié : aucune fuite vers un autre élève).

## Module Emploi du temps (Direction des Études, Préfet, Enseignant, Élève, Parent)

- La Direction des Études crée les créneaux (`/direction-etudes/emploi-du-temps`) avec
  **détection automatique de conflits** (`app/services/schedule.py`) : un même enseignant,
  une même salle ou une même classe ne peuvent jamais être programmés sur deux créneaux qui
  se chevauchent — vérifié via de vraies tentatives de création en conflit (enseignant, salle
  *et* classe simultanément) qui sont toutes rejetées sans rien écrire en base.
- La création est une route dédiée gated par `schedule.manage`, distincte de la vue partagée
  gated par `schedule.view_all` (même schéma que les bulletins) : le Préfet, qui partage
  l'accès à la page, ne peut jamais créer ni supprimer un créneau (vérifié 403 backend).
- Export **PDF** imprimable, filtrable par classe/enseignant/salle.
- C'est cette table qui constitue désormais l'affectation formelle enseignant↔classe : les
  modules Notes et Présence l'utilisent pour restreindre les choix d'un enseignant à ses
  seuls créneaux réels (vérifié : liste déroulante réduite aux affectations réelles, 403 sur
  une classe non affectée devinée par URL).
- Enseignant, Élève et Parent consultent leur propre emploi du temps en lecture seule.

## Module Préinscription (public + Préfet)

- Formulaire public (`/preinscription`, limité à 5 soumissions/heure par IP) : élève, parent/
  tuteur, classe demandée (choisie parmi les classes réellement offertes cette année), photo
  et bulletin scolaire en pièces jointes optionnelles. Génère un **numéro de dossier**
  `CSJ-<année>-XXXXX` (même compteur générique que les reçus) affiché sur une page de
  confirmation que le candidat peut noter.
- Les fichiers sont validés avant écriture sur disque — type MIME déclaré contre une liste
  autorisée et taille réelle lue depuis le flux (pas la valeur `Content-Length` fournie par le
  client) — vérifié : un exécutable déguisé et un fichier surdimensionné sont tous deux
  rejetés avant tout accès disque (`app/services/uploads.py`).
- Le Préfet instruit les dossiers (`/prefet/preinscriptions`) : changement de statut (soumis →
  en examen/incomplet), et actions terminales accepter/refuser. **Accepter crée réellement
  l'élève** (`StudentProfile` + `Enrollment` dans la classe demandée, vérifié en base) — le
  dossier n'est pas qu'une case cochée, il devient un compte d'élève exploitable par les
  autres modules.
- Seul le Préfet gère les dossiers (`applications.manage`) ; vérifié 403 pour Comptable et
  Direction des Études. La page de confirmation reste publique (aucune permission).

## Module Discipline (Directeur de Discipline, Préfet, Parent)

- Le Directeur de Discipline signale des **incidents** (`/discipline/incidents`) et y attache
  des **mesures** (avertissement, sanction, exclusion). Il crée des **convocations**
  (`/discipline/convocations`) ciblant un parent réellement lié à l'élève (via `ParentStudent`
  — pas de contact libre), avec le cycle de statuts complet créée → envoyée → vue → confirmée
  → terminée.
- La **fiche disciplinaire** (`/discipline/eleves/<id>`) réunit présences, incidents et
  convocations dans un seul document — le même service (`app/services/discipline.py`) que
  celui déjà utilisé par le tableau de bord Élève, pour que les chiffres ne divergent jamais
  d'un écran à l'autre (vérifié : le nombre de retards affiché correspond exactement entre la
  fiche et le tableau de bord de l'élève lui-même).
- Le Préfet consulte tout en lecture seule (`discipline.view_all`) ; vérifié 403 sur toute
  tentative d'écriture. La **Direction des Études n'a aucun accès** aux données
  disciplinaires — vérifié 403 sur toutes les routes, conformément à la confidentialité
  stricte exigée par le brief.
- Le **Parent** voit les convocations concernant son enfant et peut confirmer sa présence — la
  page marque automatiquement une convocation « envoyée » comme « vue » dès que le parent
  l'ouvre. Vérifié : un parent ne peut ni voir ni confirmer une convocation d'un enfant qui
  n'est pas le sien (403), et le changement de statut se répercute immédiatement côté
  Directeur de Discipline.

## Module Notifications (transversal, tous les rôles)

- Service central (`app/services/notifications.py`) bâti autour d'un registre
  `CHANNEL_DISPATCHERS` : les canaux `web` et **`email`** sont réellement implémentés (SMTP
  standard via `smtplib`, sans dépendance à un fournisseur précis — Gmail, Office365, ou tout
  serveur mail de l'établissement), les canaux `sms`/`whatsapp` restent des stubs (conforme au
  brief : ne pas implémenter tous les fournisseurs immédiatement, mais prévoir l'extension
  sans réécriture — brancher un fournisseur SMS/WhatsApp plus tard ne change aucun appel à
  `notify()` dans le reste du code).
- Le canal email reste en mode « log seulement » tant que `MAIL_SERVER` n'est pas renseigné
  dans `.env` (voir `.env.example`) — un déploiement sans serveur mail configuré continue de
  fonctionner normalement, seul l'envoi hors plateforme est sauté. Vérifié : avec
  `MAIL_SERVER` vide, `notify(..., channels=(web, email))` crée bien les deux lignes
  `Notification` sans exception.
- Cinq déclencheurs réels sont câblés dans les modules existants : convocation marquée
  « envoyée » (Discipline), absence/retard signalé — uniquement sur un changement réel de
  statut, pas à chaque réenregistrement, pour ne pas spammer le parent (Enseignant), paiement
  enregistré (Comptable), bulletin généré — notifie à la fois l'élève et son/ses parent(s)
  (Direction des Études).
- Chaque notification porte une `related_url` propre au destinataire (ex. le reçu d'un paiement
  pointe vers `parent.receipt_download`, jamais vers la route `comptable.*` équivalente, qui
  renverrait 403 à un parent) ; cliquer « marquer comme lue » redirige directement vers ce
  document.
- Un badge de compteur (notifications non lues) s'affiche dans l'en-tête sur toutes les pages
  du portail (`inject_unread_notifications_count`, context processor global).
- Vérifié en conditions réelles (pas seulement sur les données de seed) : déclenchement d'une
  convocation, d'un paiement, d'une absence/retard et d'une génération de bulletin en direct —
  chaque notification créée avec la bonne `related_url`, chaque URL testée avec le compte du
  destinataire réel (200, jamais 403). Vérifié aussi : aucune notification dupliquée en
  réenregistrant la même présence, badge décrémenté correctement après lecture, et un
  utilisateur ne peut ni voir ni marquer comme lue la notification d'un autre (403).

## Module Site public élargi (Préfet + visiteurs)

- Quatre nouvelles pages publiques : **à propos**, **vie scolaire** (contenu institutionnel
  statique), **actualités** (liste des annonces publiées + événements à venir) et **galerie**
  (photos issues des actualités publiées, plus les photos importées via `photos_ecole/`, voir
  ci-dessous). Liens ajoutés à la navigation du site public.
- Modèles `Announcement` et `Event` (`app/models/content.py`). Une actualité a un cycle
  **brouillon → publié** explicite : elle n'apparaît sur aucune page publique tant que le
  Préfet ne l'a pas publiée — vérifié en créant une actualité en direct (404 sur sa page de
  détail tant qu'elle est en brouillon, 200 dès la publication).
- Les images jointes (actualités **et** événements) réutilisent le modèle `Document` déjà
  existant (même validation MIME/taille qu'en préinscription), plutôt qu'un champ image ad
  hoc — cohérence avec le reste du système d'upload.
- Gestion réservée au Préfet (`content.manage`, même logique de supervision globale que les
  préinscriptions) : créer/publier/dépublier/supprimer une actualité, créer/supprimer un
  événement (avec image optionnelle pour les deux). Vérifié 403 pour un autre rôle
  (Comptable) sur `/prefet/actualites`.
- La page d'accueil affiche un **carrousel de photos** en défilement automatique (CSS pur,
  crossfade, sans JavaScript ni dépendance externe — cohérent avec la contrainte
  faible-bande-passante du projet) et illustre les actualités/événements récents avec de
  vraies photos de l'école quand elles sont disponibles.

### Alimenter la galerie avec des photos de l'école

```bash
mkdir photos_ecole                # une seule fois (ou lancé automatiquement au premier essai)
# déposer des photos .jpg/.jpeg/.png/.webp dans ce dossier
python import_gallery_photos.py   # importe les nouvelles photos dans la galerie publique
```

Le script est idempotent : relancé après l'ajout de nouvelles photos, il n'importe que
celles qui ne sont pas déjà en galerie (comparaison par nom de fichier). Chaque photo passe
par la même validation que les autres uploads du système (type MIME, taille max 5 Mo) avant
d'être copiée dans `instance/uploads/gallery/` et rendue visible sur `/galerie`. Le dossier
`photos_ecole/` reste local (exclu du dépôt via `.gitignore`) — ce n'est qu'une zone de dépôt
temporaire, pas le stockage définitif.

## Module Bibliothèque numérique (Enseignant, Élève, Parent, Direction des Études)

- L'Enseignant dépose des **supports de cours** et des **devoirs** (`/enseignant/bibliotheque`)
  pour ses propres classes/matières, avec fichier joint optionnel (PDF ou image, même
  validation que les autres uploads du système). Le choix classe/matière est restreint aux
  combinaisons réellement affectées dans l'emploi du temps (`teacher_affectations`, même
  scoping que Notes et Présence) — pas de simple croisement libre de deux listes.
- L'**Élève** et le **Parent** consultent en lecture seule la bibliothèque de leur propre
  classe (`/eleve/bibliotheque`, `/parent/enfants/<id>/bibliotheque`) et peuvent télécharger
  les fichiers joints. Vérifié : un élève d'une autre classe ne voit ni le contenu ni ne peut
  télécharger le fichier en devinant son URL (403), un parent ne peut consulter que la
  bibliothèque de ses propres enfants (403 sur un enfant qui n'est pas le sien).
- La **Direction des Études** (et le Préfet) supervisent toutes les classes en lecture seule
  (`library.view_all`, `/direction-etudes/bibliotheque`) — aucune action d'écriture possible,
  vérifié 403 sur la route de gestion enseignant.
- Vérifié en conditions réelles : dépôt d'un support avec fichier joint par un enseignant,
  téléchargement réussi par l'enseignant lui-même, par l'élève de la bonne classe et par son
  parent (200 partout), refus pour un élève d'une autre classe (403), suppression refusée à
  un autre enseignant que le propriétaire (403) puis acceptée pour le propriétaire (avec
  suppression en cascade du fichier joint).

## Module Rapports avancés (Préfet)

- Trois rapports consolidés (`/prefet/rapports`), chacun consultable à l'écran et
  exportable en PDF : **présence** (absences/retards/taux de présence par classe sur une
  période choisie), **financier** (attendu/encaissé/solde global et par type de frais,
  dépenses, net) et **académique** (moyenne générale par classe, top 5 / bottom 5 des
  élèves de l'établissement pour un trimestre).
- Le service `app/services/reports.py` ne recalcule jamais la logique métier lui-même : il
  agrège ce que les services existants (finance, notes, présence) exposent déjà, pour ne
  jamais afficher un chiffre qui diverge de ce que montrent les autres écrans.
- Réservé au Préfet (`reports.view`) — vérifié 403 pour le Comptable et pour la Direction des
  Études (qui n'a accès qu'à sa propre supervision Notes/Bibliothèque, pas à la vue
  consolidée). Vérifié aussi : les 3 PDF se génèrent correctement (200,
  `Content-Type: application/pdf`) avec des chiffres cohérents avec les données seed.

## Module Administration (Super Admin)

Complète ce qui n'était que des pages de lecture seule marquées « module suivant » depuis le
squelette P0.

- **Utilisateurs** (`/admin/utilisateurs`) : créer un compte (email, téléphone, mot de passe,
  rôles multiples), modifier un compte existant (rôles, statut actif/désactivé, réinitialiser
  le mot de passe — laissé vide, il n'est pas changé). Le rôle `SUPER_ADMIN` lui-même n'est
  jamais proposé dans la liste de rôles assignables (pas d'auto-élévation de privilège
  possible depuis cette interface).
- **Paramètres** (`/admin/parametres`) : édition de l'identité de l'établissement (nom, ville,
  province, pays, devise) et de l'**identité visuelle** — logo et couleurs primaire/secondaire
  sont maintenant réellement appliqués sur tout le site (auparavant stockés en base mais
  jamais lus nulle part : le logo était codé en dur et les couleurs CSS étaient des valeurs
  fixes indépendantes de la base). Un logo non défini retombe sur le logo par défaut du dépôt.
- **Années scolaires** : création d'une nouvelle année (libellé, dates) et bascule de l'année
  « en cours » — une seule à la fois, la précédente est automatiquement désactivée.
- Vérifié en conditions réelles : modification des couleurs/logo → répercutée immédiatement
  sur la page d'accueil publique ; création d'un utilisateur → connexion réussie avec le bon
  rôle et redirection vers le bon tableau de bord ; désactivation d'un compte → connexion
  refusée (message générique, ne révèle pas si le compte existe) ; réactivation → connexion de
  nouveau possible ; bascule d'année scolaire → l'ancienne et la nouvelle ne sont jamais
  toutes les deux « en cours » en même temps ; toutes les routes admin vérifiées 403 pour un
  Préfet.
- **Journal d'audit** (`/admin/journal`) : `log_action()` — appelé à ~40 endroits sensibles
  dans toute l'application (connexion, paiement, note modifiée, sanction, changement de rôle,
  suppression...) depuis le tout premier squelette P0 — n'écrivait jusqu'ici que dans le
  logger applicatif, jamais en base malgré ce que documentait son propre commentaire
  (« sera remplacé par une écriture dans la table AuditLog »). Cette table existe maintenant
  réellement (`app/models/system.py`) et `log_action()` y écrit à chaque appel, **sans
  modifier aucun des ~40 sites d'appel existants** — c'était tout l'intérêt du point d'entrée
  unique dès la conception initiale. Consultable et filtrable (par action, par compte) avec
  pagination, réservé au Super Admin (`admin.view_audit_log`).
- Vérifié en conditions réelles : une connexion et une création d'utilisateur ont bien créé
  des lignes `AuditLog` avec le bon `user_id`/IP/horodatage ; un paiement enregistré a bien
  stocké son `new_value` sous forme de JSON structuré (`{amount, currency, student_id}`),
  affiché correctement dans le journal ; filtre par action et par compte fonctionnels ; 403
  pour un Préfet.

## Installation locale

```bash
python -m venv .venv
.venv/Scripts/activate   # ou source .venv/bin/activate sous Linux/Mac
pip install -r requirements.txt
cp .env.example .env     # puis adapter les valeurs
```

## Base de données

```bash
export FLASK_APP=wsgi.py
flask db upgrade          # applique les migrations (crée data/csj_dev.db en SQLite par défaut)
python seed_demo.py       # jeu de données démo (voir identifiants ci-dessous)
```

## Lancer le serveur

```bash
python wsgi.py
```

Le site est disponible sur http://127.0.0.1:5000 (port configurable via `PORT`).

## Comptes de démonstration

Mot de passe commun : `Demo2026!` (sauf le compte Super Admin, voir `.env`).

| Rôle | Email |
|---|---|
| Super Admin | défini par `ADMIN_EMAIL` / `ADMIN_MOT_DE_PASSE` dans `.env` |
| Préfet des Études | prefet.demo@csjerusalem.cd |
| Directeur des Études | directeur.etudes.demo@csjerusalem.cd |
| Directeur de Discipline | directeur.discipline.demo@csjerusalem.cd |
| Enseignant | enseignant1.demo@csjerusalem.cd … enseignant5.demo@csjerusalem.cd |
| Comptable | comptable1.demo@csjerusalem.cd, comptable2.demo@csjerusalem.cd |
| Parent | parent1.demo@csjerusalem.cd … parent10.demo@csjerusalem.cd |
| Élève | eleve.csj-2026-0001@csjerusalem.cd (+ 0002, 0003) |

Toutes les entités démo sont marquées `is_demo=True` en base — elles ne doivent jamais être
confondues avec des données réelles d'exploitation.

## Sécurité (P0)

- Mots de passe hachés (Werkzeug PBKDF2), jamais stockés en clair.
- Verrouillage de compte après 5 échecs de connexion (15 minutes), limitation de débit sur
  `/auth/connexion` (Flask-Limiter).
- CSRF activé sur tous les formulaires (Flask-WTF).
- Permissions vérifiées côté backend sur chaque route (`@require_permission`), jamais
  seulement par masquage de menu côté template.
- Secrets (clé Flask, identifiants base de données, mot de passe admin) exclusivement via
  variables d'environnement — jamais commités dans le dépôt.
- `FLASK_ENV=development` est le **seul** moyen d'autoriser des valeurs de secours pour
  `SECRET_KEY`/`ADMIN_MOT_DE_PASSE` (nécessaire en local). Sans cette variable — donc en
  production par défaut — le démarrage échoue si ces secrets ne sont pas explicitement
  fournis, pour ne jamais déployer accidentellement avec les identifiants par défaut visibles
  dans ce dépôt (même convention que le projet Majt Shop).

## Déploiement en production

Déploiement sur **Render**, même plateforme que le projet Majt Shop.

### 1. Base de données MySQL

Créer une nouvelle base MySQL (une base dédiée, séparée de celle de Majt Shop) chez le même
hébergeur MySQL déjà utilisé pour Majt Shop, et noter la chaîne de connexion au format :

```
mysql+pymysql://<utilisateur>:<mot_de_passe>@<hôte>:<port>/<nom_base>
```

### 2. Dépôt GitHub

```bash
git remote add origin <url-du-dépôt-github>
git push -u origin main
```

(Le dépôt local est déjà initialisé avec un premier commit — `git init` a été fait, mais
aucun remote ni push n'a été exécuté automatiquement : c'est une étape volontairement
laissée à l'utilisateur.)

### 3. Service Render

`render.yaml` est déjà présent à la racine — sur Render, choisir *New > Blueprint* et pointer
vers le dépôt GitHub : Render lit `render.yaml` et pré-remplit le service. Variables
d'environnement à renseigner manuellement dans le tableau de bord Render (marquées
`sync: false` dans `render.yaml`, donc non générées automatiquement) :

| Variable | Valeur |
|---|---|
| `DATABASE_URL` | la chaîne de connexion MySQL de l'étape 1 |
| `ADMIN_MOT_DE_PASSE` | mot de passe réel du compte Super Admin — **à changer**, ne pas garder la valeur de développement |
| `MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD` | uniquement si le canal email des notifications doit être actif dès le lancement (sinon laisser vide, le site fonctionne normalement sans) |

`SECRET_KEY` est généré automatiquement par Render (`generateValue: true`). `preDeployCommand:
flask db upgrade` applique les migrations automatiquement à chaque déploiement, avant que la
nouvelle version ne reçoive du trafic.

### 4. Après le premier déploiement

- Se connecter avec `ADMIN_EMAIL` / `ADMIN_MOT_DE_PASSE` définis en variables d'environnement.
- **Ne pas lancer `seed_demo.py` en production** — il crée des comptes et données de
  démonstration (`is_demo=True`) qui n'ont pas leur place sur une instance réelle. Créer les
  vrais comptes (enseignants, comptables, etc.) via `/admin/utilisateurs`, et la vraie année
  scolaire via `/admin/parametres`.
- **Stockage des fichiers uploadés (limite connue)** : les documents/photos téléversés
  (`instance/uploads/`) sont écrits sur le disque local du service. Sur le plan gratuit de
  Render, ce disque est **éphémère** — tout fichier téléversé est perdu à chaque redéploiement
  ou redémarrage du service. Pour un usage réel où les documents doivent persister (logo,
  photos de galerie, pièces jointes de préinscription, supports de cours), ajouter un
  [disque persistant Render](https://render.com/docs/disks) monté sur `instance/uploads`, ou
  migrer vers un stockage objet externe (S3-compatible) — non fait dans cette session, à
  prévoir avant une mise en production avec de vrais uploads.

## Prochaines étapes

P0, P1 et P2 sont complets (site public élargi, bibliothèque numérique, rapports avancés,
administration Super Admin — utilisateurs, paramètres, années scolaires, identité visuelle,
journal d'audit réellement persisté). Le canal email des notifications est réellement branché
(SMTP, voir `.env.example`). Les cartes statistiques restées en placeholder « module à venir »
depuis le squelette P0 initial (Direction des Études, Enseignant, Élève, Parent, Préfet) ont
été remplacées par des données réelles au fil des modules livrés depuis. Reste en P3 : les
canaux SMS et WhatsApp, qui nécessitent de choisir un fournisseur (Africa's Talking, Twilio,
WhatsApp Cloud API...) et d'obtenir des identifiants — une décision propre à l'établissement,
pas prise dans cette
session.
