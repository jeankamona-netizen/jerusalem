from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, TextAreaField, TimeField
from wtforms.validators import DataRequired, Length, Optional

from app.models import DisciplinaryAction, DisciplinaryIncident


class IncidentForm(FlaskForm):
    student_profile_id = SelectField("Élève", coerce=int, validators=[DataRequired()])
    date = DateField("Date", validators=[DataRequired()])
    severity = SelectField(
        "Gravité",
        choices=[(code, label) for code, label in DisciplinaryIncident.SEVERITY_LABELS.items()],
        validators=[DataRequired()],
    )
    description = TextAreaField("Description des faits", validators=[DataRequired(), Length(max=1000)])


class ActionForm(FlaskForm):
    type = SelectField(
        "Type",
        choices=[(code, label) for code, label in DisciplinaryAction.TYPE_LABELS.items()],
        validators=[DataRequired()],
    )
    date = DateField("Date", validators=[DataRequired()])
    details = TextAreaField("Détails", validators=[Optional(), Length(max=500)])


class ConvocationForm(FlaskForm):
    parent_profile_id = SelectField("Parent / Tuteur à convoquer", coerce=int, validators=[DataRequired()])
    motif = StringField("Motif", validators=[DataRequired(), Length(max=500)])
    date = DateField("Date", validators=[DataRequired()])
    heure = TimeField("Heure", validators=[DataRequired()])
    lieu = StringField("Lieu", default="Bureau de la Discipline", validators=[DataRequired(), Length(max=200)])
    commentaire = TextAreaField("Commentaire", validators=[Optional(), Length(max=500)])
