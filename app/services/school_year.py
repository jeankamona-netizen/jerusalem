from app.models import SchoolYear


def get_current_school_year(school_id):
    return SchoolYear.query.filter_by(school_id=school_id, is_current=True).first()
