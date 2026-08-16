from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class FeeType(db.Model, TimestampMixin):
    """Type de frais configurable par année scolaire (brief section 19) : jamais de
    montant codé en dur dans le code, tout passe par cette table."""

    __tablename__ = "fee_types"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    school_year_id = db.Column(db.Integer, db.ForeignKey("school_years.id"), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    label = db.Column(db.String(150), nullable=False)
    default_amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="CDF")

    school_year = db.relationship("SchoolYear")

    def __repr__(self):
        return f"<FeeType {self.label}>"


class Fee(db.Model, TimestampMixin):
    """Montant dû par un élève pour un type de frais donné, pour une année scolaire."""

    __tablename__ = "fees"

    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    fee_type_id = db.Column(db.Integer, db.ForeignKey("fee_types.id"), nullable=False)
    school_year_id = db.Column(db.Integer, db.ForeignKey("school_years.id"), nullable=False)
    amount_due = db.Column(db.Numeric(12, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=True)

    student = db.relationship("StudentProfile")
    fee_type = db.relationship("FeeType")
    payments = db.relationship("Payment", back_populates="fee")

    @property
    def amount_paid(self):
        return sum((p.amount for p in self.payments), start=0)

    @property
    def balance(self):
        return self.amount_due - self.amount_paid

    def __repr__(self):
        return f"<Fee student={self.student_profile_id} fee_type={self.fee_type_id}>"


class Payment(db.Model, TimestampMixin, SoftDeleteMixin):
    """Un paiement enregistré par un comptable. `fee_id` est nullable pour accepter un
    versement libre non encore rattaché à un frais précis (cas fréquent en pratique)."""

    __tablename__ = "payments"

    METHOD_ESPECES = "especes"
    METHOD_MOBILE_MONEY = "mobile_money"
    METHOD_BANQUE = "banque"
    METHOD_AUTRE = "autre"
    METHOD_CHOICES = (METHOD_ESPECES, METHOD_MOBILE_MONEY, METHOD_BANQUE, METHOD_AUTRE)
    METHOD_LABELS = {
        METHOD_ESPECES: "Espèces",
        METHOD_MOBILE_MONEY: "Mobile Money",
        METHOD_BANQUE: "Banque",
        METHOD_AUTRE: "Autre",
    }

    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    fee_id = db.Column(db.Integer, db.ForeignKey("fees.id"), nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="CDF")
    method = db.Column(db.String(20), nullable=False, default=METHOD_ESPECES)
    reference = db.Column(db.String(100), nullable=True)
    recorded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    comment = db.Column(db.String(300), nullable=True)

    student = db.relationship("StudentProfile")
    fee = db.relationship("Fee", back_populates="payments")
    recorded_by = db.relationship("User")
    receipt = db.relationship("Receipt", back_populates="payment", uselist=False)

    def __repr__(self):
        return f"<Payment {self.amount} {self.currency} student={self.student_profile_id}>"


class Receipt(db.Model, TimestampMixin):
    __tablename__ = "receipts"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"), unique=True, nullable=False)
    number = db.Column(db.String(30), unique=True, nullable=False)
    pdf_path = db.Column(db.String(500), nullable=True)

    payment = db.relationship("Payment", back_populates="receipt")

    def __repr__(self):
        return f"<Receipt {self.number}>"


class Expense(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    school_year_id = db.Column(db.Integer, db.ForeignKey("school_years.id"), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="CDF")
    expense_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(300), nullable=True)
    recorded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    recorded_by = db.relationship("User")

    def __repr__(self):
        return f"<Expense {self.category} {self.amount}>"
