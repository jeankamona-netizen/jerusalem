from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import DateField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.models import Announcement, Event

UPLOAD_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]


class AnnouncementForm(FlaskForm):
    title = StringField("Titre", validators=[DataRequired(), Length(max=200)])
    body = TextAreaField("Contenu", validators=[DataRequired()])
    category = SelectField(
        "Catégorie",
        choices=[(code, label) for code, label in Announcement.CATEGORY_LABELS.items()],
        validators=[DataRequired()],
    )
    image = FileField("Image (optionnelle)", validators=[Optional(), FileAllowed(UPLOAD_EXTENSIONS)])


class EventForm(FlaskForm):
    title = StringField("Titre", validators=[DataRequired(), Length(max=200)])
    date = DateField("Date", validators=[DataRequired()])
    category = SelectField(
        "Catégorie",
        choices=[(code, label) for code, label in Event.CATEGORY_LABELS.items()],
        validators=[DataRequired()],
    )
    description = TextAreaField("Description", validators=[Optional(), Length(max=1000)])
    image = FileField("Image (optionnelle)", validators=[Optional(), FileAllowed(UPLOAD_EXTENSIONS)])
