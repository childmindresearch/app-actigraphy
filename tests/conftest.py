"""Pytest configuration file."""

import datetime
from collections.abc import Generator

import pytest
import pytest_mock
from sqlalchemy import orm

from actigraphy.database import database, models


@pytest.fixture()
def session(in_memory_db: database.Database) -> Generator[orm.Session, None, None]:
    """Returns a database session in memory.

    Returns:
        A database session.
    """
    db_session = in_memory_db.session_factory()
    yield db_session
    db_session.close()


@pytest.fixture(autouse=True)
def in_memory_db(mocker: pytest_mock.MockFixture) -> database.Database:
    """Fixture to monckeypatch the database."""
    db = database.Database(":memory:")
    db.create_database()
    mocker.patch("actigraphy.database.database.Database", return_value=db)
    return db


@pytest.fixture(autouse=True)
def _fill_database(session: orm.Session) -> None:
    """Fill the database with dummy data."""
    subject = models.Subject(name="subject", n_points_per_day=1)
    day = models.Day(
        date=datetime.date(1993, 8, 26),
        subject=subject,
    )
    sleep_time = models.SleepTime(
        onset=datetime.datetime(1993, 8, 26, 12, 0, 0).replace(tzinfo=datetime.UTC),
        onset_utc_offset=0,
        wakeup=datetime.datetime(1993, 8, 26, 13, 0, 0).replace(tzinfo=datetime.UTC),
        wakeup_utc_offset=0,
        day=day,
    )

    session.add_all((subject, day, sleep_time))
    session.commit()


@pytest.fixture()
def file_manager() -> dict[str, str]:
    """Return a file manager dictionary."""
    return {
        "identifier": "subject",
        "database": "",
        "multiple_sleeplog_file": "",
        "missing_sleep_file": "",
        "review_night_file": "",
        "data_cleaning_file": "",
    }
