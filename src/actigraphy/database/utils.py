"""Standard CRUD operations for the database."""

import datetime
import logging
import pathlib
from collections.abc import Iterable
from typing import TypedDict

import numpy as np
from sqlalchemy import orm

from actigraphy.core import config
from actigraphy.database import models
from actigraphy.io import ggir_files

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME
DEFAULT_SLEEP_TIME = settings.DEFAULT_SLEEP_TIME

logger = logging.getLogger(LOGGER_NAME)


def initialize_datapoints(
    ggir_metadata: ggir_files.MetaData,
) -> list[models.DataPoint]:
    """Initialize the data points for the given subject.

    Args:
        ggir_metadata: The path to the ggir_files file for the subject.

    Returns:
        list[models.DataPoint]: The initialized data points.

    """
    logger.debug("Initializing data points.")
    window_size_ratio = ggir_metadata.m.windowsizes[1] // ggir_metadata.m.windowsizes[0]
    non_wear_elements = np.where(ggir_metadata.m.metalong["nonwearscore"] > 1)[0]
    non_wear_indices_in_data = [
        element * window_size_ratio for element in non_wear_elements
    ]
    non_wear_indices = np.concatenate(
        [
            np.arange(index, index + window_size_ratio)
            for index in non_wear_indices_in_data
        ],
    )
    return [
        _metashort_row_to_sql_datapoint(row, non_wear=index in non_wear_indices)  # type: ignore[arg-type, unused-ignore] # pre-commit mypy flags this, local mypy does not.
        for index, row in enumerate(ggir_metadata.m.metashort.iter_rows(named=True))
    ]


def initialize_ms4_sleep_times(
    ggir_ms4: ggir_files.MS4,
    day: datetime.datetime,
    index: int,
) -> tuple[list[models.SleepTime], list[models.GGIRSleepTime]]:
    """Initializes a list of SleepTime objects.

    Args:
        ggir_ms4: The ggir_ms4 object containing sleep data.
        day: The day for which sleep times are being initialized.
        index: The index of the sleep data in ggir_ms4.

    Returns:
        models.SleepTime: The initialized sleep times.
    """
    logger.debug("Initializing MS4 sleep times.")
    onset = ggir_ms4.dataframe["sleeponset_ts"][index]
    wakeup = ggir_ms4.dataframe["wakeup_ts"][index]

    def timestamp2datetime(
        timestamp: str,
        day: datetime.datetime,
        offset: int,
    ) -> datetime.datetime:
        time = datetime.time.fromisoformat(timestamp)
        date = datetime.datetime.combine(day.date(), time)
        return date - datetime.timedelta(seconds=offset)

    utc_offset: int = (
        0 if day.utcoffset() is None else int(day.utcoffset().total_seconds())  # type: ignore[union-attr]
    )
    onset_time = timestamp2datetime(onset, day, utc_offset)
    wakeup_time = timestamp2datetime(wakeup, day, utc_offset)

    if datetime.time.fromisoformat(onset).hour < 12:  # noqa: PLR2004
        onset_time += datetime.timedelta(days=1)
    if onset_time > wakeup_time:
        wakeup_time += datetime.timedelta(days=1)

    return [
        models.SleepTime(
            onset=onset_time,
            onset_utc_offset=utc_offset,
            wakeup=wakeup_time,
            wakeup_utc_offset=utc_offset,
        ),
    ], [
        models.GGIRSleepTime(
            onset=onset_time,
            onset_utc_offset=utc_offset,
            wakeup=wakeup_time,
            wakeup_utc_offset=utc_offset,
        ),
    ]


def initialize_default_sleep_times(
    day: datetime.datetime,
) -> list[models.SleepTime]:
    """Initializes the default sleep times for the given day.

    Args:
        day: The day to initialize the default sleep times for.

    Returns:
        list[models.SleepTime]: The initialized default sleep times.
    """
    logger.debug("Initializing default sleep times.")
    offset = 0 if day.utcoffset() is None else int(day.utcoffset().total_seconds())  # type: ignore[union-attr]
    onset_wakeup = datetime.datetime.combine(
        day.date(),
        DEFAULT_SLEEP_TIME,
    ) - datetime.timedelta(seconds=offset)

    return [
        models.SleepTime(
            onset=onset_wakeup,
            onset_utc_offset=offset,
            wakeup=onset_wakeup,
            wakeup_utc_offset=offset,
        ),
    ]


def initialize_days(
    ggir_metadata: ggir_files.MetaData,
    ggir_ms4: ggir_files.MS4,
) -> list[models.Day]:
    """Initialize the days for the given subject.

    Args:
        ggir_metadata: The path to the ggir metadata file for the subject.
        ggir_ms4: The path to the ggir ms4 file for the subject.

    Returns:
        list[models.Day]: The initialized days.

    """
    logger.debug("Initializing days.")
    raw_dates = [
        datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z")
        for date in ggir_metadata.m.metashort["timestamp"]
    ]
    dates = sorted(_keep_last_unique_date(raw_dates))

    day_models = []
    ms4_dates = ggir_ms4.dataframe["calendar_date"]
    for day_index in range(len(dates)):
        day = dates[day_index]
        day_model = models.Day(date=day.date())
        day_as_ms4_format = day.strftime("%-d/%-m/%Y")
        try:
            ms4_index = ms4_dates.to_list().index(day_as_ms4_format)
        except ValueError:
            ms4_index = None

        if ms4_index is None:
            day_model.sleep_times = initialize_default_sleep_times(day)
        else:
            (
                day_model.sleep_times,
                day_model.ggir_sleep_times,
            ) = initialize_ms4_sleep_times(
                ggir_ms4,
                day,
                ms4_index,
            )
        day_models.append(day_model)
    return day_models


def initialize_subject(
    identifier: str,
    ggir_metadata_file: str | pathlib.Path,
    ggir_ms4_file: str | pathlib.Path,
    session: orm.Session,
) -> models.Subject:
    """Initializes a new subject with the given identifier and ggir_files file.

    Args:
        identifier: The identifier for the new subject.
        ggir_metadata_file: The path to the ggir file for the new subject.
        ggir_ms4_file: The path to the ggir ms4 file for the new subject.
        session: The database session.

    Returns:
        models.Subject: The initialized subject object.

    Notes:
        Default sleep times are set to 03:00 the next day.
        Last day is not included as it doesn't include a night.
    """
    logger.debug("Initializing subject %s", identifier)
    ggir_metadata = ggir_files.MetaData.from_file(ggir_metadata_file)
    ggir_ms4 = ggir_files.MS4.from_file(ggir_ms4_file)

    day_models = initialize_days(ggir_metadata, ggir_ms4)
    data_points = initialize_datapoints(ggir_metadata)

    n_points_per_day = 86400 // ggir_metadata.m.windowsizes[0]
    subject = models.Subject(
        name=identifier,
        days=day_models,
        n_points_per_day=n_points_per_day,
        data_points=data_points,
    )
    session.add_all([subject, *data_points])
    session.commit()
    return subject


def find_closest_datapoint(
    date_time: datetime.datetime,
    session: orm.Session,
    window_size: int = 1440,
) -> models.DataPoint:
    """Find the closest datapoint to the given timezone unaware date time.

    Args:
        date_time: The date time to find the closest datapoint for.
        session: The database session.
        window_size: The window size in minutes in which to look
            for the closest datapoint. Defaults to 1440 (a full day).

    Returns:
        models.DataPoint: The closest datapoint.

    Notes:
        This function cannot accurately determine the closest datapoint if
        there are multiple datapoints with the same timestamp (i.e. in a
        timezone switch). However, in the current implementation, this should
        not be an issue.
    """
    date_time_no_tz = date_time.replace(tzinfo=None)
    data_points = (
        session.query(models.DataPoint)
        .filter(
            models.DataPoint.timestamp
            >= date_time_no_tz - datetime.timedelta(minutes=window_size / 2),
            models.DataPoint.timestamp
            <= date_time_no_tz + datetime.timedelta(minutes=window_size / 2),
        )
        .order_by(
            models.DataPoint.timestamp,
            models.DataPoint.timestamp_utc_offset,
        )
    )
    time_deltas = [
        abs((data_point.timestamp - date_time_no_tz).total_seconds())
        for data_point in data_points
    ]
    return data_points[np.argmin(time_deltas)]  # type: ignore[no-any-return]


class MetaShortRow(TypedDict):
    """Represents a row in the metashort table.

    Attributes:
        timestamp: The timestamp of the data point.
        anglez: The angle of the data point.
        ENMO: The ENMO of the data point.
    """

    timestamp: str
    anglez: float
    ENMO: float


def _metashort_row_to_sql_datapoint(
    row: MetaShortRow,
    *,
    non_wear: bool,
) -> models.DataPoint:
    """Convert a ggir_files row to a SQL datapoint object.

    Args:
        row: The ggir_files row containing the datapoint information.
        non_wear: Indicates whether the datapoint represents non-wear.

    Returns:
        models.DataPoint: The converted SQL datapoint object.
    """
    return models.DataPoint(
        timestamp=datetime.datetime.strptime(
            row["timestamp"],
            "%Y-%m-%dT%H:%M:%S%z",
        ).astimezone(datetime.UTC),
        timestamp_utc_offset=datetime.datetime.strptime(
            row["timestamp"],
            "%Y-%m-%dT%H:%M:%S%z",
        )
        .utcoffset()
        .total_seconds(),  # type: ignore[union-attr]
        sensor_angle=row["anglez"],
        sensor_acceleration=row["ENMO"],
        non_wear=non_wear,
    )


def _keep_last_unique_date(
    datetimes: Iterable[datetime.datetime],
) -> list[datetime.datetime]:
    """Fetch unique dates.

    Args:
        datetimes: A list of datetime objects.

    Returns:
        list[datetime.datetime]: A list of datetime objects with unique dates
            The last occurence of the sorted dates is retained.
    """
    unique_dates = set()
    result = []

    sorted_dates = sorted(datetimes)
    for dt in sorted_dates[::-1]:
        dt_date = dt.date()
        if dt_date not in unique_dates:
            unique_dates.add(dt_date)
            result.append(dt)

    return result
