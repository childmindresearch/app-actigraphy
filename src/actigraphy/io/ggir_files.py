"""Functions for reading and writing minor files to a format accepted by GGIR."""

import csv
import dataclasses
import datetime
import logging
import pathlib
import re
from collections import abc
from typing import Any

import pandas as pd
import polars as pl
import pydantic
import rdata

from actigraphy.core import config
from actigraphy.database import crud, database

settings = config.get_settings()

LOGGER_NAME = settings.LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


class MetaDataM(pydantic.BaseModel):
    """A Pydantic model representing the M subclass of the metadata for actigraphy data.

    Only the required data is retained.

    Attributes:
        model_config: A dictionary containing configuration options for the model.
        metalong: A pandas DataFrame containing long-format metadata.
        metashort : A pandas DataFrame containing short-format metadata.
        windowsizes: A list of integers representing window sizes for the data.
    """

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)
    metalong: pl.DataFrame
    metashort: pl.DataFrame
    windowsizes: list[int]


class MetaData(pydantic.BaseModel):
    """A class representing metadata for actigraphy data.

    Attributes:
        m: The metadata object.

    Methods:
        from_file(cls, filepath: str | pathlib.Path) -> "MetaData": Reads a
        metadata file from disk and returns a Metadata object.
    """

    m: MetaDataM

    @classmethod
    def from_file(cls, filepath: str | pathlib.Path) -> "MetaData":
        """Load metadata from a file.

        Args:
            filepath: The path to the metadata file.

        Returns:
            MetaData: An instance of the MetaData class with the loaded metadata.
        """
        metadata = _rdata_to_datadict(filepath)
        metadata_clean = _recursive_clean_rdata(metadata)
        return cls(**metadata_clean)


@dataclasses.dataclass
class MS4:
    """Represents an MS4 file containing actigraphy data.

    Attributes:
        rows: A list of MS4Row objects representing the actigraphy data.
    """

    dataframe: pl.DataFrame

    @classmethod
    def from_file(cls, filepath: str | pathlib.Path) -> "MS4":
        """Reads an MS4 file from disk and returns an MS4 object.

        Args:
            filepath: The path to the MS4 file.

        Returns:
            An MS4 object containing the data from the file.
        """
        dataframe = _rdata_to_datadict(filepath)
        dataframe_clean = _recursive_clean_rdata(dataframe)
        return cls(dataframe_clean["nightsummary"])


def write_sleeplog(file_manager: dict[str, str]) -> None:
    """Save the given hour vector to a CSV file.

    Args:
        file_manager: A dictionary containing file paths for the sleep log file.

    Notes:
        The last day is discarded as each frontend "day" displays two days.
        If no data is available, a placeholder time is used as a default.

    """
    logger.debug("Writing sleep log file.")
    session = next(database.session_generator(file_manager["database"]))
    subject = crud.read_subject(session, file_manager["identifier"])
    placeholder_time = datetime.datetime(
        1970,
        1,
        1,
        0,
        0,
        0,
        tzinfo=datetime.UTC,
    )

    onset_times = []
    wakeup_times = []
    for day in subject.days:
        if len(day.sleep_times) == 0:
            onset_times.append(placeholder_time)
            wakeup_times.append(placeholder_time)
            continue
        longest_window = max(enumerate(day.sleep_times), key=lambda x: x[1].duration)[0]
        onset_times.append(day.sleep_times[longest_window].onset_with_tz)
        wakeup_times.append(day.sleep_times[longest_window].wakeup_with_tz)

    dates = _flatten(zip(onset_times, wakeup_times, strict=True))

    data_line = [file_manager["identifier"]]
    data_line.extend([str(date) for date in dates])

    sleep_times = _flatten(
        [[f"onset_N{day + 1}", f"wakeup_N{day + 1}"] for day in range(len(dates) // 2)],
    )
    header = ["ID", *sleep_times]

    with open(file_manager["sleeplog_file"], "w") as file_buffer:
        writer = csv.writer(file_buffer)
        writer.writerow(header)
        writer.writerow(data_line)


def write_all_sleep_times(file_manager: dict[str, str]) -> None:
    """Writes all sleep times to a CSV file.

    Args:
        file_manager: A dictionary containing file paths for the sleep log file.

    """
    logger.debug("Writing all sleep times file.")
    session = next(database.session_generator(file_manager["database"]))
    subject = crud.read_subject(session, file_manager["identifier"])
    onsets = [time.onset_with_tz for day in subject.days for time in day.sleep_times]
    wakeups = [time.wakeup_with_tz for day in subject.days for time in day.sleep_times]

    csv_output = pd.DataFrame(
        {
            "onset": onsets,
            "wakeup": wakeups,
        },
    ).sort_values(by="onset")
    csv_output.to_csv(file_manager["all_sleep_times"], index=False)


def write_data_cleaning(file_manager: dict[str, str]) -> None:
    """Write a list of values to a CSV file.

    Args:
        file_manager: A dictionary containing file paths for the data cleaning file.

    """
    session = next(database.session_generator(file_manager["database"]))
    subject = crud.read_subject(session, file_manager["identifier"])
    has_no_sleep_windows = [len(day.sleep_times) == 0 for day in subject.days]
    is_missing_sleep = [day.is_missing_sleep for day in subject.days]
    ignore_night = [
        int(has_no_sleep_windows[i] or is_missing_sleep[i])
        for i in range(len(subject.days))
    ]

    header = ["ID", "day_part5", "relyonguider_part4", "night_part4"]
    indices = [i + 1 for i, value in enumerate(ignore_night) if value == 1]
    data = [
        file_manager["identifier"],
        "",
        "",
        " ".join([str(value) for value in indices]),
    ]
    with open(file_manager["data_cleaning_file"], "w") as file_buffer:
        writer = csv.writer(file_buffer)
        writer.writerow(header)
        writer.writerow(data)


def _flatten(iterable_of_iterables: abc.Iterable[Any]) -> list[Any]:
    """Recursively flattens an iterable of iterables into a single list.

    Args:
        iterable_of_iterables: The list of lists to flatten.

    Returns:
        list[any]: The flattened list.
    """
    new_list = []
    for item in iterable_of_iterables:
        if isinstance(item, abc.Iterable) and not isinstance(item, str | bytes):
            new_list.extend(_flatten(item))
        else:
            new_list.append(item)
    return new_list


def _clean_key(key: str) -> str:
    """Replaces strings with snakecase characters and legal attribute names.

    Args:
        key: The key name to clean.

    Returns:
        A cleaned key.

    """
    key = key.replace(".", "_")
    return _snakecase(key)


def _clean_value(value: Any) -> Any:  # noqa: ANN401
    """Cleans a value."""
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


def _recursive_clean_rdata(r_data: dict[str, Any]) -> dict[str, Any]:
    """Cleans the .rdata input file.

    Replaces dictionary keys with snakecase characters and legal attribute names and
    replaces pandas dataframes with polars dataframes.

    Args:
        r_data: The dictionary to clean.

    Returns:
        A dictionary with cleaned keys.

    Notes:
        - This function acts recursively on nested dictionaries.
        - Replaces `.` in keys with `_`.
        - Sets all attributes to snakecase.
        - Replaces single length lists in dictionary values with their first element.

    """
    cleaned_rdata = {}
    for key, value in r_data.items():
        clean_key = _clean_key(key)
        clean_value = _clean_value(value)
        if isinstance(value, dict):
            clean_value = _recursive_clean_rdata(clean_value)
        elif isinstance(value, pd.DataFrame):
            clean_value = pl.from_pandas(clean_value)
        cleaned_rdata[clean_key] = clean_value
    return cleaned_rdata


def _rdata_to_datadict(filepath: str | pathlib.Path) -> dict[str, Any]:
    """Converts an Rdata file to a pandas dataframe.

    Args:
        filepath: The path to the Rdata file.

    Returns:
        dict[str, Any]: A dictionary containing the data from the Rdata file.
    """
    data = rdata.parser.parse_file(filepath)
    return rdata.conversion.convert(data)  # type: ignore[no-any-return]


def _snakecase(string: str) -> str:
    """Converts a string to snake case.

    Args:
        string: The string to convert.

    Returns:
        The converted string.

    Notes:
        Consecutive uppercase letters do not receive underscores between them.

    """
    return re.sub(r"(?<=[A-Z])(?!$)(?!_)(?![A-Z])", "_", string[::-1]).lower()[::-1]
