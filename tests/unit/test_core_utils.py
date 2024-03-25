"""Tests the core utilities."""

import datetime

from actigraphy.core import utils


def test_time2point() -> None:
    """Test that time2point returns the time difference in minutes."""
    time = datetime.datetime.fromisoformat("1993-08-26T15:00:00").replace(
        tzinfo=datetime.UTC,
    )
    date = datetime.date.fromisoformat("1993-08-26")
    expected = 180

    actual = utils.time2point(time, date, None)

    assert actual == expected


def test_point2time() -> None:
    """Test that point2time returns the new time."""
    point = 180
    date = datetime.date.fromisoformat("1993-08-26")
    expected = datetime.datetime.fromisoformat("1993-08-26T15:00:00.000000").replace(
        tzinfo=datetime.UTC,
    )

    actual = utils.point2time(point, date, 0, None, None)

    assert actual == expected
