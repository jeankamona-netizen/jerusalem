from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.models import Payment


class FeeTypeForm(FlaskForm):
    code = StringField("Code", validators=[DataRequired(), Length(max=50)])
    label = StringField("Libellé", validators=[DataRequired(), Length(max=150)])
    default_amount = DecimalField("Montant par défaut", validators=[DataRequired(), NumberRange(min=0)])
    currency = StringField("Devise", default="CDF", validators=[DataRequired(), Length(max=10)])


class PaymentForm(FlaskForm):
    fee_id = SelectField("Frais concerné", coerce=int, validators=[Optional()])
    amount = DecimalField("Montant versé", validators=[DataRequired(), NumberRange(min=0.01)])
    currency = StringField("Devise", default="CDF", validators=[DataRequired(), Length(max=10)])
    method = SelectField(
        "Mode de paiement",
        choices=[(code, label) for code, label in Payment.METHOD_LABELS.items()],
        validators=[DataRequired()],
    )
    reference = StringField("Référence", validators=[Optional(), Length(max=100)])
    payment_date = DateField("Date de paiement", validators=[DataRequired()])
    comment = TextAreaField("Commentaire", validators=[Optional(), Length(max=300)])


class ExpenseForm(FlaskForm):
    category = StringField("Catégorie", validators=[DataRequired(), Length(max=100)])
    amount = DecimalField("Montant", validators=[DataRequired(), NumberRange(min=0.01)])
    currency = StringField("Devise", default="CDF", validators=[DataRequired(), Length(max=10)])
    expense_date = DateField("Date", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[Optional(), Length(max=300)])
