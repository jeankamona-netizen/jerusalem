from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, DateField, PasswordField, SelectMultipleField, StringField
from wtforms.validators import DataRequired, Email, Length, Optional
from wtforms.widgets import CheckboxInput, ListWidget

from app import constants

LOGO_UPLOAD_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]


class SettingsForm(FlaskForm):
    name = StringField("Nom de l'établissement", validators=[DataRequired(), Length(max=200)])
    city = StringField("Ville", validators=[DataRequired(), Length(max=120)])
    province = StringField("Province", validators=[DataRequired(), Length(max=120)])
    country = StringField("Pays", validators=[DataRequired(), Length(max=120)])
    currency_default = StringField("Devise par défaut", validators=[DataRequired(), Length(max=10)])
    primary_color = StringField("Couleur primaire", validators=[Optional(), Length(max=20)])
    secondary_color = StringField("Couleur secondaire", validators=[Optional(), Length(max=20)])
    logo = FileField("Logo (optionnel)", validators=[Optional(), FileAllowed(LOGO_UPLOAD_EXTENSIONS)])


class SchoolYearForm(FlaskForm):
    label = StringField("Libellé (ex: 2026-2027)", validators=[DataRequired(), Length(max=20)])
    start_date = DateField("Date de début", validators=[DataRequired()])
    end_date = DateField("Date de fin", validators=[DataRequired()])


class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class UserForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField("Téléphone", validators=[Optional(), Length(max=30)])
    password = PasswordField(
        "Mot de passe",
        validators=[Optional(), Length(min=8, message="8 caractères minimum.")],
    )
    roles = MultiCheckboxField(
        "Rôles",
        choices=[(code, label) for code, label in constants.ROLE_LABELS.items() if code != constants.SUPER_ADMIN],
    )
    is_active_account = BooleanField("Compte actif", default=True)
