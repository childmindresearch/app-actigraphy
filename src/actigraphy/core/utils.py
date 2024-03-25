"""Utility functions for the actigraphy package."""

import datetime
import logging
import os
import pathlib
from os import path

from actigraphy.core import config

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME
N_SLIDER_STEPS = settings.N_SLIDER_STEPS

logger = logging.getLogger(LOGGER_NAME)


class FileManager:
    """A class for managing file paths and directories.

    Attributes:
        base_dir (str): The base directory for the file manager.
        database (str): The path to the database file.
        log_dir (str): The directory for log files.
        identifier (str): The identifier for the file manager.
        log_file (str): The path to the log file.
        sleeplog_file (str): The path to the sleep log file.
        data_cleaning_file (str): The path to the data cleaning file.
        metadata_file (str): The path to the metadata file.

    Notes:
        Files are kept as strings because Dash cannot serialize pathlib.Path.
    """

    def __init__(self, base_dir: str | pathlib.Path) -> None:
        """Initializes the FileManager class."""
        self.base_dir = str(base_dir)
        self.database = path.join(self.base_dir, "actigraphy.sqlite")
        self.log_dir = path.join(self.base_dir, "logs")
        self.identifier = self.base_dir.rsplit("_", maxsplit=1)[-1]

        self.log_file = path.join(self.log_dir, "log_file.csv")
        self.sleeplog_file = path.join(self.log_dir, f"sleeplog_{self.identifier}.csv")
        self.data_cleaning_file = path.join(
            self.log_dir,
            f"data_cleaning_{self.identifier}.csv",
        )
        self.all_sleep_times = path.join(
            self.log_dir,
            f"multiple_sleep_{self.identifier}.csv",
        )
        self.ms4_file = path.join(
            self.base_dir,
            "meta",
            "ms4.out",
            self.identifier + ".gt3x.RData",
        )
        metadata_dir = path.join(self.base_dir, "meta", "basic")
        self.metadata_file = str(next(pathlib.Path(metadata_dir).glob("meta_*")))

        os.makedirs(self.log_dir, exist_ok=True)


def time2point(
    time: datetime.datetime,
    date: datetime.date,
    daylight_savings_shift: int | None,
) -> int:
    """Converts a datetime to the number of minutes since the given day's midnight.

    Args:
        time: The datetime object to convert.
        date: The date preceding midnight as reference.
        daylight_savings_shift: The difference in seconds caused by daylight
            savings time.

    Returns:
        float: The number of minutes since midnight on the given date.
    """
    logger.debug("Converting time to point: %s.", time)
    reference = datetime.datetime.combine(
        date,
        datetime.time(hour=12),
        tzinfo=time.tzinfo,
    )

    delta = time - reference
    if daylight_savings_shift is None:
        return int(delta.total_seconds() // 60)
    return int(delta.total_seconds() // 60) + daylight_savings_shift // 60


def point2time(
    point: float,
    date: datetime.date,
    timezone_offset: int,
    daylight_savings_timepoint: str | None,
    daylight_savings_shift: int | None,
) -> datetime.datetime:
    """Converts a slider point value to a datetime object.

    This function accounts for daylight savings time in its output.

    Args:
        point: The point value to convert.
        date: The date to combine with the converted time.
        timezone_offset: Timezone offset in seconds.
        daylight_savings_timepoint: The timepoint at which daylight savings time
            starts.
        daylight_savings_shift: The seconds offset due to daylight savings.

    Returns:
        datetime.datetime: The resulting datetime object.

    """
    logger.debug("Converting point to time: %s.", point)
    if daylight_savings_shift is None:
        daylight_savings_shift = 0

    minutes_in_36_hours = 36 * 60
    total_minutes = minutes_in_36_hours + daylight_savings_shift // 60
    n_minutes = point / N_SLIDER_STEPS * total_minutes

    days, remainder_minutes = divmod(n_minutes, 1440)
    hours, minutes = divmod(remainder_minutes, 60)

    slider_offset = datetime.timedelta(hours=12)

    delta = datetime.timedelta(days=days, hours=hours, minutes=minutes) + slider_offset
    adjusted_time = datetime.datetime.combine(date, datetime.time(0)) + delta

    timezone_delta = datetime.timedelta(seconds=timezone_offset)
    tz_info = datetime.timezone(timezone_delta)
    time_with_tz = adjusted_time.replace(tzinfo=tz_info)
    if daylight_savings_timepoint is not None:
        daylight_savings_time = datetime.datetime.strptime(
            daylight_savings_timepoint,
            "%Y-%m-%d %H:%M:%S%z",
        )

        if time_with_tz >= daylight_savings_time:
            time_with_tz = time_with_tz.astimezone(
                datetime.timezone(
                    timezone_delta - datetime.timedelta(seconds=daylight_savings_shift),
                ),
            )
    return time_with_tz
