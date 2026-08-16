from app.extensions import db
from app.models.mixins import TimestampMixin


class Room(db.Model, TimestampMixin):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f"<Room {self.name}>"


class Schedule(db.Model, TimestampMixin):
    """Un créneau hebdomadaire (classe/matière/enseignant/salle/jour/heures) pour une année
    scolaire. C'est cette table qui constitue l'affectation formelle enseignant↔classe :
    une fois peuplée, les modules Notes et Présence restreignent le choix de classe/matière
    d'un enseignant aux seuls créneaux qui lui sont réellement affectés ici (voir
    app/services/schedule.py:teacher_affectations)."""

    __tablename__ = "schedules"

    DAY_LUNDI = "LUN"
    DAY_MARDI = "MAR"
    DAY_MERCREDI = "MER"
    DAY_JEUDI = "JEU"
    DAY_VENDREDI = "VEN"
    DAY_SAMEDI = "SAM"
    DAY_CHOICES = (DAY_LUNDI, DAY_MARDI, DAY_MERCREDI, DAY_JEUDI, DAY_VENDREDI, DAY_SAMEDI)
    DAY_LABELS = {
        DAY_LUNDI: "Lundi",
        DAY_MARDI: "Mardi",
        DAY_MERCREDI: "Mercredi",
        DAY_JEUDI: "Jeudi",
        DAY_VENDREDI: "Vendredi",
        DAY_SAMEDI: "Samedi",
    }
    DAY_ORDER = {code: index for index, code in enumerate(DAY_CHOICES)}

    id = db.Column(db.Integer, primary_key=True)
    school_year_id = db.Column(db.Integer, db.ForeignKey("school_years.id"), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    teacher_profile_id = db.Column(db.Integer, db.ForeignKey("teacher_profiles.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=True)

    day = db.Column(db.String(3), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    school_year = db.relationship("SchoolYear")
    classe = db.relationship("Classe")
    subject = db.relationship("Subject")
    teacher = db.relationship("TeacherProfile")
    room = db.relationship("Room")

    def __repr__(self):
        return f"<Schedule {self.classe_id} {self.subject_id} {self.day} {self.start_time}>"
