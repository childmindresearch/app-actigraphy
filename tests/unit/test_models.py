"""Tests for the database models."""

import datetime

import pytest
import sqlalchemy
from sqlalchemy import orm

from actigraphy.database import models


def test_create_sleep_time(session: orm.Session) -> None:
    """Test the creation of a SleepTime instance."""
    sleep_time = models.SleepTime(
        onset=datetime.datetime.now(),
        onset_utc_offset=0,
        wakeup=datetime.datetime.now(),
        wakeup_utc_offset=0,
        day_id=1,
    )

    session.add(sleep_time)
    session.commit()

    assert sleep_time.id is not None
    assert sleep_time.time_created is not None
    assert sleep_time.time_updated is not None


def test_create_day(session: orm.Session) -> None:
    """Test the creation of a Day instance."""
    day = models.Day(date=datetime.date.today(), subject_id=1)

    session.add(day)
    session.commit()

    assert day.id is not None
    assert day.time_created is not None
    assert day.time_updated is not None


def test_create_subject(session: orm.Session) -> None:
    """Test the creation of a Subject instance."""
    subject = models.Subject(name="test", n_points_per_day=1)

    session.add(subject)
    session.commit()

    assert subject.id is not None
    assert subject.time_created is not None
    assert subject.time_updated is not None


def test_sleep_time_day_relationship(session: orm.Session) -> None:
    """Test the relationship between SleepTime and Day."""
    day = models.Day(date=datetime.date.today(), subject_id=1)
    sleep_time = models.SleepTime(
        onset=datetime.datetime.now(),
        onset_utc_offset=0,
        wakeup=datetime.datetime.now(),
        wakeup_utc_offset=0,
        day=day,
    )

    session.add(day)
    session.commit()

    assert sleep_time.day == day
    assert sleep_time.id is not None
    assert sleep_time.day_id == day.id


def test_day_subject_relationship(session: orm.Session) -> None:
    """Test the relationship between Day and Subject."""
    subject = models.Subject(name="test", n_points_per_day=1)
    day = models.Day(date=datetime.date.today(), subject=subject)

    session.add(day)
    session.commit()

    assert day.subject == subject
    assert day.id is not None
    assert subject.id is not None
    assert day.subject_id == subject.id


def test_unique_day_subject_constraint(session: orm.Session) -> None:
    """Test the unique constraint of Subject name."""
    subject = models.Subject(name="test")
    day_1 = models.Day(date=datetime.date.today(), subject=subject)
    day_2 = models.Day(date=datetime.date.today(), subject=subject)

    session.add_all((subject, day_1, day_2))
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        session.commit()


def test_with_tz_properties(session: orm.Session) -> None:
    """Test the onset_with_tz property of SleepTime."""
    onset = datetime.datetime(2023, 1, 1, 12, 0).replace(tzinfo=datetime.UTC)
    sleep_time = models.SleepTime(
        onset=onset,
        onset_utc_offset=3600,  # 1 hour in seconds
        wakeup=onset + datetime.timedelta(hours=8),
        wakeup_utc_offset=3600,
        day_id=1,
    )
    expected_onset_with_tz = onset.astimezone(
        datetime.timezone(datetime.timedelta(seconds=3600)),
    )
    expected_wakeup_with_tz = (onset + datetime.timedelta(hours=8)).astimezone(
        datetime.timezone(datetime.timedelta(seconds=3600)),
    )

    session.add(sleep_time)
    session.commit()

    assert sleep_time.onset_with_tz == expected_onset_with_tz
    assert sleep_time.wakeup_with_tz == expected_wakeup_with_tz
