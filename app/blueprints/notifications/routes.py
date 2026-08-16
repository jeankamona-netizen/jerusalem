from flask import abort, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.blueprints.notifications import notifications_bp
from app.extensions import db
from app.models import Notification
from app.models.mixins import utcnow


@notifications_bp.route("/")
@login_required
def list_notifications():
    notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template("notifications/list.html", notifications=notifications)


@notifications_bp.route("/<int:notification_id>/lire", methods=["POST"])
@login_required
def mark_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        abort(403)

    if not notification.read_at:
        notification.read_at = utcnow()
        db.session.commit()

    return redirect(notification.related_url or url_for("notifications.list_notifications"))


@notifications_bp.route("/tout-lire", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, read_at=None).update({"read_at": utcnow()})
    db.session.commit()
    return redirect(url_for("notifications.list_notifications"))
