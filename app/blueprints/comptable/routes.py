import datetime
import os
from decimal import Decimal

from flask import abort, flash, redirect, render_template, send_file, url_for
from flask_login import current_user

from app import constants
from app.blueprints.comptable import comptable_bp
from app.blueprints.comptable.forms import ExpenseForm, FeeTypeForm, PaymentForm
from app.extensions import db
from app.models import Expense, Fee, FeeType, Notification, Payment, Receipt, StudentProfile
from app.services.audit import log_action
from app.services.finance import active_students_query, student_balance
from app.services.notifications import notify
from app.services.pdf import generate_and_save_receipt, next_document_number, receipt_pdf_path
from app.services.permissions import require_permission, sidebar_items_for
from app.services.school_year import get_current_school_year


@comptable_bp.route("/")
@require_permission(constants.DASHBOARD_COMPTABLE)
def dashboard():
    school_year = get_current_school_year(current_user.school_id)
    stats = {"recettes_jour": Decimal("0"), "recettes_mois": Decimal("0"), "a_jour": 0, "partiel": 0, "retard": 0}

    if school_year:
        today = datetime.date.today()
        payments = (
            Payment.query.join(StudentProfile)
            .filter(StudentProfile.school_id == current_user.school_id, Payment.deleted_at.is_(None))
            .all()
        )
        stats["recettes_jour"] = sum(
            (p.amount for p in payments if p.payment_date == today), start=Decimal("0")
        )
        stats["recettes_mois"] = sum(
            (p.amount for p in payments if p.payment_date.year == today.year and p.payment_date.month == today.month),
            start=Decimal("0"),
        )
        for student in active_students_query(school_year):
            due, paid, balance = student_balance(student, school_year)
            if due == 0:
                continue
            if balance <= 0:
                stats["a_jour"] += 1
            elif paid > 0:
                stats["partiel"] += 1
            else:
                stats["retard"] += 1

    return render_template(
        "dashboard/comptable/dashboard.html",
        sidebar_items=sidebar_items_for(current_user),
        stats=stats,
        school_year=school_year,
    )


@comptable_bp.route("/frais", methods=["GET", "POST"])
@require_permission(constants.FINANCE_MANAGE)
def fee_types():
    school_year = get_current_school_year(current_user.school_id)
    if not school_year:
        flash("Aucune année scolaire active configurée.", "error")
        return redirect(url_for("comptable.dashboard"))

    form = FeeTypeForm()
    if form.validate_on_submit():
        fee_type = FeeType(
            school_id=current_user.school_id,
            school_year_id=school_year.id,
            code=form.code.data.strip(),
            label=form.label.data.strip(),
            default_amount=form.default_amount.data,
            currency=form.currency.data.strip().upper(),
        )
        db.session.add(fee_type)
        db.session.flush()

        # Un nouveau type de frais s'applique automatiquement à chaque élève actif de
        # l'année scolaire en cours (évite une étape manuelle d'assignation par élève).
        created_count = 0
        for student in active_students_query(school_year):
            exists = Fee.query.filter_by(
                student_profile_id=student.id, fee_type_id=fee_type.id, school_year_id=school_year.id
            ).first()
            if not exists:
                db.session.add(
                    Fee(
                        student_profile_id=student.id,
                        fee_type_id=fee_type.id,
                        school_year_id=school_year.id,
                        amount_due=fee_type.default_amount,
                    )
                )
                created_count += 1

        db.session.commit()
        log_action("fee_type_created", entity_type="FeeType", entity_id=fee_type.id)
        flash(f"Frais « {fee_type.label} » créé et appliqué à {created_count} élève(s).", "info")
        return redirect(url_for("comptable.fee_types"))

    all_fee_types = FeeType.query.filter_by(school_year_id=school_year.id).order_by(FeeType.label).all()
    return render_template(
        "dashboard/comptable/fee_types.html",
        sidebar_items=sidebar_items_for(current_user),
        form=form,
        fee_types=all_fee_types,
        school_year=school_year,
    )


@comptable_bp.route("/eleves")
@require_permission(constants.FINANCE_MANAGE)
def students():
    school_year = get_current_school_year(current_user.school_id)
    rows = []
    if school_year:
        for student in active_students_query(school_year):
            due, paid, balance = student_balance(student, school_year)
            rows.append({"student": student, "due": due, "paid": paid, "balance": balance})

    return render_template(
        "dashboard/comptable/students.html",
        sidebar_items=sidebar_items_for(current_user),
        rows=rows,
        school_year=school_year,
    )


@comptable_bp.route("/eleves/<int:student_id>/paiement", methods=["GET", "POST"])
@require_permission(constants.FINANCE_MANAGE)
def record_payment(student_id):
    student = StudentProfile.query.get_or_404(student_id)
    if student.school_id != current_user.school_id:
        abort(404)

    school_year = get_current_school_year(current_user.school_id)
    if not school_year:
        flash("Aucune année scolaire active configurée.", "error")
        return redirect(url_for("comptable.students"))

    fees = Fee.query.filter_by(student_profile_id=student.id, school_year_id=school_year.id).all()

    form = PaymentForm()
    form.fee_id.choices = [(f.id, f"{f.fee_type.label} — solde {f.balance:.2f} {f.fee_type.currency}") for f in fees]
    if not form.is_submitted():
        form.payment_date.data = datetime.date.today()

    if form.validate_on_submit():
        fee = next((f for f in fees if f.id == form.fee_id.data), None)
        if not fee:
            abort(400)

        payment = Payment(
            student_profile_id=student.id,
            fee_id=fee.id,
            amount=form.amount.data,
            currency=form.currency.data.strip().upper(),
            method=form.method.data,
            reference=form.reference.data.strip() if form.reference.data else None,
            recorded_by_user_id=current_user.id,
            payment_date=form.payment_date.data,
            comment=form.comment.data.strip() if form.comment.data else None,
        )
        db.session.add(payment)
        db.session.flush()

        receipt = Receipt(
            payment_id=payment.id,
            number=next_document_number(Receipt, form.payment_date.data.year),
        )
        db.session.add(receipt)
        db.session.flush()

        generate_and_save_receipt(payment, receipt, current_user.school)

        for parent in student.parents:
            notify(
                parent.user,
                Notification.TYPE_PAIEMENT,
                title=f"Paiement enregistré — {student.full_name}",
                body=f"{payment.amount:.2f} {payment.currency} pour {fee.fee_type.label}. Reçu {receipt.number}.",
                related_url=url_for("parent.receipt_download", receipt_id=receipt.id),
            )

        db.session.commit()

        log_action(
            "payment_recorded",
            entity_type="Payment",
            entity_id=payment.id,
            new_value={"amount": str(payment.amount), "currency": payment.currency, "student_id": student.id},
        )
        flash(f"Paiement enregistré. Reçu {receipt.number} généré.", "info")
        return redirect(url_for("comptable.receipt_download", receipt_id=receipt.id))

    due, paid, balance = student_balance(student, school_year)
    return render_template(
        "dashboard/comptable/record_payment.html",
        sidebar_items=sidebar_items_for(current_user),
        form=form,
        student=student,
        fees=fees,
        due=due,
        paid=paid,
        balance=balance,
    )


@comptable_bp.route("/recus/<int:receipt_id>.pdf")
@require_permission(constants.FINANCE_MANAGE)
def receipt_download(receipt_id):
    receipt = Receipt.query.get_or_404(receipt_id)
    payment = receipt.payment
    if payment.student.school_id != current_user.school_id:
        abort(404)

    path = receipt_pdf_path(receipt.number)
    if not os.path.exists(path):
        generate_and_save_receipt(payment, receipt, current_user.school)

    return send_file(path, mimetype="application/pdf", download_name=f"{receipt.number}.pdf")


@comptable_bp.route("/depenses", methods=["GET", "POST"])
@require_permission(constants.FINANCE_MANAGE)
def expenses():
    form = ExpenseForm()
    if not form.is_submitted():
        form.expense_date.data = datetime.date.today()

    if form.validate_on_submit():
        school_year = get_current_school_year(current_user.school_id)
        expense = Expense(
            school_id=current_user.school_id,
            school_year_id=school_year.id if school_year else None,
            category=form.category.data.strip(),
            amount=form.amount.data,
            currency=form.currency.data.strip().upper(),
            expense_date=form.expense_date.data,
            description=form.description.data.strip() if form.description.data else None,
            recorded_by_user_id=current_user.id,
        )
        db.session.add(expense)
        db.session.commit()
        log_action("expense_recorded", entity_type="Expense", entity_id=expense.id)
        flash("Dépense enregistrée.", "info")
        return redirect(url_for("comptable.expenses"))

    all_expenses = (
        Expense.query.filter_by(school_id=current_user.school_id, deleted_at=None)
        .order_by(Expense.expense_date.desc())
        .all()
    )
    total = sum((e.amount for e in all_expenses), start=Decimal("0"))
    return render_template(
        "dashboard/comptable/expenses.html",
        sidebar_items=sidebar_items_for(current_user),
        form=form,
        expenses=all_expenses,
        total=total,
    )
