from flask_wtf import FlaskForm
from wtforms import SelectField, TimeField
from wtforms.validators import DataRequired, Optional

from app.models import Schedule


class ScheduleForm(FlaskForm):
    classe_id = SelectField("Classe", coerce=int, validators=[DataRequired()])
    subject_id = SelectField("Matière", coerce=int, validators=[DataRequired()])
    teacher_profile_id = SelectField("Enseignant", coerce=int, validators=[DataRequired()])
    room_id = SelectField("Salle", validators=[Optional()])
    day = SelectField(
        "Jour",
        choices=[(code, label) for code, label in Schedule.DAY_LABELS.items()],
        validators=[DataRequired()],
    )
    start_time = TimeField("Heure de début", validators=[DataRequired()])
    end_time = TimeField("Heure de fin", validators=[DataRequired()])
