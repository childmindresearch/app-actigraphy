"""Utility functions used across components."""

import datetime
import functools
import logging

from actigraphy.core import config
from actigraphy.database import crud, database, models

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


@functools.cache
def get_day_data(
    day_index: int,
    database_path: str,
    identifier: str,
) -> list[models.DataPoint]:
    """Get data for a given day.

    Args:
        day_index: The index of the day for which to retrieve the data.
        database_path: The path to the database.
        identifier: The identifier for the participant.

    Returns:
        list[models.DataPoint]: A list of data points for the given day.

    """
    logger.debug("Getting data for day %s", day_index)
    session = next(database.session_generator(database_path))
    subject = crud.read_subject(session, identifier)
    day = crud.read_day_by_subject(session, day_index, identifier)
    return (
        session.query(models.DataPoint)
        .filter(
            models.DataPoint.subject_id == subject.id,
            models.DataPoint.timestamp
            >= datetime.datetime.combine(
                day.date - datetime.timedelta(days=1),
                datetime.time(hour=11),
            ),
            models.DataPoint.timestamp
            <= datetime.datetime.combine(
                day.date + datetime.timedelta(days=3),
                datetime.time(hour=1),
            ),
        )
        .order_by(models.DataPoint.timestamp, models.DataPoint.timestamp_utc_offset)
        .all()
    )
