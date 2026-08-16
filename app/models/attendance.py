from app.extensions import db
from app.models.mixins import TimestampMixin


class Attendance(db.Model, TimestampMixin):
    """Présence d'un élève, prise par un enseignant (`recorded_by_user_id`) pour une
    classe/date/matière donnée. `subject_id` nullable : certains appels (ex: appel général du
    matin) ne sont pas rattachés à une matière précise.

    Statuts gardés en constantes de classe (pas de table séparée) — même convention que
    Payment.METHOD_* et Enrollment.STATUS_* : trois valeurs fixes, pas de configuration
    dynamique nécessaire en P0."""

    __tablename__ = "attendances"

    STATUS_PRESENT = "present"
    STATUS_ABSENT = "absent"
    STATUS_RETARD = "retard"
    STATUS_CHOICES = (STATUS_PRESENT, STATUS_ABSENT, STATUS_RETARD)
    STATUS_LABELS = {STATUS_PRESENT: "Présent", STATUS_ABSENT: "Absent", STATUS_RETARD: "Retard"}

    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)
    school_year_id = db.Column(db.Integer, db.ForeignKey("school_years.id"), nullable=False)

    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    arrival_time = db.Column(db.Time, nullable=True)
    comment = db.Column(db.String(300), nullable=True)
    justified = db.Column(db.Boolean, nullable=False, default=False)
    recorded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    student = db.relationship("StudentProfile")
    classe = db.relationship("Classe")
    subject = db.relationship("Subject")
    recorded_by = db.relationship("User")

    def __repr__(self):
        return f"<Attendance student={self.student_profile_id} date={self.date} status={self.status}>"
