from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import DateField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional

RELATION_CHOICES = [("Père", "Père"), ("Mère", "Mère"), ("Tuteur", "Tuteur"), ("Autre", "Autre")]
UPLOAD_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "pdf"]


class ApplicationForm(FlaskForm):
    # Élève
    nom = StringField("Nom", validators=[DataRequired(), Length(max=120)])
    postnom = StringField("Postnom", validators=[Optional(), Length(max=120)])
    prenom = StringField("Prénom", validators=[Optional(), Length(max=120)])
    sexe = SelectField("Sexe", choices=[("M", "Masculin"), ("F", "Féminin")], validators=[DataRequired()])
    date_naissance = DateField("Date de naissance", validators=[DataRequired()])
    lieu_naissance = StringField("Lieu de naissance", validators=[Optional(), Length(max=150)])
    nationalite = StringField("Nationalité", default="Congolaise", validators=[Optional(), Length(max=80)])
    adresse = TextAreaField("Adresse", validators=[Optional(), Length(max=300)])
    ancienne_ecole = StringField("Ancienne école", validators=[Optional(), Length(max=200)])
    classe_demandee_id = SelectField("Classe demandée", coerce=int, validators=[DataRequired()])

    # Parent / tuteur
    parent_nom = StringField("Nom complet du parent/tuteur", validators=[DataRequired(), Length(max=120)])
    parent_telephone = StringField("Téléphone", validators=[DataRequired(), Length(max=30)])
    parent_email = StringField("Email", validators=[Optional(), Email(), Length(max=255)])
    parent_adresse = TextAreaField("Adresse du parent/tuteur", validators=[Optional(), Length(max=300)])
    parent_relation = SelectField("Relation avec l'élève", choices=RELATION_CHOICES, validators=[DataRequired()])

    # Documents (optionnels — la famille peut les apporter plus tard au secrétariat)
    photo = FileField("Photo de l'élève", validators=[Optional(), FileAllowed(UPLOAD_EXTENSIONS)])
    document_scolaire = FileField(
        "Bulletin / document scolaire", validators=[Optional(), FileAllowed(UPLOAD_EXTENSIONS)]
    )
