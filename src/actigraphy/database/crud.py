"""Standard CRUD operations for the database."""

from sqlalchemy import orm

from actigraphy.core import exceptions
from actigraphy.database import models


def read_subject(
    session: orm.Session,
    subject_name: str,
) -> models.Subject:
    """Reads a subject from the database.

    Args:
        session: The database session.
        subject_name: The name of the subject to read.

    Returns:
        models.Subject: The subject model.
    """
    subject = (
        session.query(models.Subject)
        .filter(models.Subject.name == subject_name)
        .first()
    )

    if subject:
        return subject
    msg = f"Subject {subject_name} not found in database"
    raise exceptions.DatabaseError(msg)


def read_day_by_subject(
    session: orm.Session,
    day_index: int,
    subject_name: str,
) -> models.Day:
    """Reads a day from the database for a specific subject.

    Args:
        session: The database session.
        day_index: The day to read.
        subject_name: The name of the subject to read the day for.

    Returns:
        models.Day: The day model.
    """
    day = (
        session.query(models.Day)
        .join(models.Subject)
        .filter(models.Subject.name == subject_name)
        .order_by(models.Day.date)
        .offset(day_index)
        .first()
    )

    if day:
        return day
    msg = f"Day {day} not found in database for subject {subject_name}"
    raise exceptions.DatabaseError(msg)
