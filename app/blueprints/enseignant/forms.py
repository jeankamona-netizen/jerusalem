from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import DateField, DecimalField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app import constants
from app.models import CourseMaterial

LIBRARY_UPLOAD_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "webp"]


class AssessmentForm(FlaskForm):
    # Une seule liste déroulante "classe — matière" (valeur "classeId:subjectId") plutôt que
    # deux champs indépendants : ne propose que les combinaisons auxquelles l'enseignant est
    # réellement affecté dans l'emploi du temps (voir app.services.schedule.teacher_affectations),
    # un simple croisement de deux listes séparées ne pourrait pas l'empêcher de choisir une
    # combinaison classe/matière qui ne lui est pas affectée.
    classe_subject = SelectField("Classe — Matière", validators=[DataRequired()])
    assessment_type_id = SelectField("Type d'évaluation", coerce=int, validators=[DataRequired()])
    term = SelectField(
        "Trimestre",
        choices=[(code, label) for code, label in constants.TERM_LABELS.items()],
        validators=[DataRequired()],
    )
    date = DateField("Date", validators=[DataRequired()])
    coefficient = DecimalField("Coefficient", validators=[DataRequired(), NumberRange(min=0.1)])
    max_score = DecimalField("Note maximale", default=20, validators=[DataRequired(), NumberRange(min=1)])


class AttendanceSessionForm(FlaskForm):
    classe_id = SelectField("Classe", coerce=int, validators=[DataRequired()])
    subject_id = SelectField("Matière (optionnel — appel général si vide)", validators=[Optional()])
    date = DateField("Date", validators=[DataRequired()])


class CourseMaterialForm(FlaskForm):
    classe_subject = SelectField("Classe — Matière", validators=[DataRequired()])
    title = StringField("Titre", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=1000)])
    category = SelectField(
        "Catégorie",
        choices=[(code, label) for code, label in CourseMaterial.CATEGORY_LABELS.items()],
        validators=[DataRequired()],
    )
    file = FileField("Fichier (optionnel)", validators=[Optional(), FileAllowed(LIBRARY_UPLOAD_EXTENSIONS)])


class HomeworkForm(FlaskForm):
    classe_subject = SelectField("Classe — Matière", validators=[DataRequired()])
    title = StringField("Titre", validators=[DataRequired(), Length(max=200)])
    instructions = TextAreaField("Consignes", validators=[Optional(), Length(max=1000)])
    due_date = DateField("À rendre pour le", validators=[DataRequired()])
    file = FileField("Fichier (optionnel)", validators=[Optional(), FileAllowed(LIBRARY_UPLOAD_EXTENSIONS)])
