"""Functions for importing data needed for the Actigraphy graph."""
import datetime
import functools
import itertools
import logging
import pathlib
from typing import Any

import numpy as np

from actigraphy.core import config
from actigraphy.database import crud, database
from actigraphy.io import metadata

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


def _get_data_file(data_sub_dir: pathlib.Path) -> pathlib.Path:
    """Get the data file from the specified directory.

    Args:
        data_sub_dir: The directory containing the data file.

    Returns:
        pathlib.Path: The path to the data file.

    Raises:
        ValueError: If there is not exactly one data file in the directory.
    """
    data_files = list(data_sub_dir.glob("*.RData"))
    if len(data_files) == 1:
        return data_files[0]
    msg = f"Expected one data file in {data_sub_dir}, found {len(data_files)}"
    raise ValueError(msg)


@functools.lru_cache
def get_time(times: tuple[str]) -> list[datetime.datetime]:
    """Get the datetime objects from a list of times.

    Args:
        times: The metadata object.

    Returns:
        A list of datetime objects that represent the standard time.

    """
    logger.debug("Getting standard time from metadata.")
    return [datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S%z") for time in times]


@functools.cache
def get_metadata(base_dir: str | pathlib.Path) -> metadata.MetaData:
    """Get metadata from the specified base directory.

    Args:
        base_dir: The base directory to search for metadata.

    Returns:
        metadata.MetaData: The metadata object.

    """
    logger.debug("Getting metadata from %s", "base_dir")
    metadata_file = _get_data_file(pathlib.Path(base_dir) / "meta" / "basic")
    return metadata.MetaData.from_file(metadata_file)


@functools.lru_cache
def get_midnights(base_dir: str) -> list[int]:
    """Returns a list of indices of timestamps just after midnight in the metadata file.

    Args:
        base_dir: The base directory containing the metadata file.

    Returns:
        list[int]: A list of indices of midnight timestamps in the metadata file.
    """
    logger.debug("Getting midnights from %s", base_dir)
    metadata_data = get_metadata(base_dir)
    timestamps = get_time(tuple(metadata_data.m.metashort.timestamp))
    midnight_indices = [
        timestamps.index(date_pairs[1]) + 1
        for date_pairs in itertools.pairwise(timestamps)
        if date_pairs[0].day != date_pairs[1].day
    ]
    logger.debug("Found %s midnights.", len(midnight_indices))
    return midnight_indices


def get_timezone(file_manager: dict[str, str]) -> datetime.tzinfo | None:
    """Returns the timezone from the metadata.

    Args:
        file_manager: A dictionary containing the base directory of the metadata.

    Returns:
        str: The timezone extracted from the metadata.

    """
    logger.debug("Getting timezone from %s", file_manager["base_dir"])
    metadata_data = get_metadata(file_manager["base_dir"])
    timestamps = get_time(tuple(metadata_data.m.metashort.timestamp))
    return timestamps[0].tzinfo


def get_graph_data(
    file_manager: dict[str, str],
    day: int,
) -> tuple[list[float], list[float], list[int]]:
    """Loads data for a given day and prepares it for plotting.

    Args:
        file_manager: A dictionary containing file paths.
        day: The day for which to load data.

    Returns:
        tuple[list[float], list[float], list[int]]: A tuple containing three lists:
            - A list of acceleration values.
            - A list of angle values.
            - A list of non-wear values.
    """
    logger.debug("Loading data for day %s.", day)
    metadata_data = get_metadata(file_manager["base_dir"])

    # Prepare nonwear information for plotting
    enmo = metadata_data.m.metashort.ENMO.reset_index(drop=True)
    anglez = metadata_data.m.metashort.anglez.reset_index(drop=True)
    nonwear = np.zeros(len(enmo), dtype=int)

    # take instances where nonwear was detected (on ws2 time vector) and map
    # results onto a ws3 lenght vector for plotting purposes
    nonwear_elements = np.where(metadata_data.m.metalong.nonwearscore > 1)[0]

    window_size_ratio = (
        metadata_data.m.windowsizes[1] // metadata_data.m.windowsizes[0] - 1
    )
    for index in nonwear_elements:
        nonwear[index : index + window_size_ratio] = 1

    time_day_starts, time_day_ends = _day_start_and_end_time_points(
        file_manager,
        day,
        metadata_data.m.windowsizes[0],
    )

    acc = abs(enmo[time_day_starts:time_day_ends] * 1000)
    ang = anglez[time_day_starts:time_day_ends]
    non_wear = nonwear[time_day_starts:time_day_ends]

    session = next(database.session_generator(file_manager["database"]))
    subject = crud.read_subject(session, file_manager["identifier"])
    extension = [0] * (subject.n_points_per_day - len(acc))
    if time_day_starts == 0:
        action = "prepend"
    elif time_day_ends is None:
        action = "append"
    else:
        action = None

    acc = _extend_data(acc, extension, action)
    ang = _extend_data(ang, extension, action)
    non_wear_list = _extend_data(non_wear, extension, action)

    # Rescale for plotting.
    acc = [value / 14 - 210 for value in acc]

    return acc, ang, non_wear_list


def _day_start_and_end_time_points(
    file_manager: dict[str, str],
    day: int,
    window_size: int,
) -> tuple[int, int | None]:
    """Returns the start and end time points for the given day.

    Args:
        file_manager: A dictionary containing file paths.
        day : The index of the day for which to retrieve the start and end time points.
        window_size: The size of the window in minutes.

    Returns:
        tuple[int, int | None]: A tuple containing the start and end time points
            for the given day.
    """
    target_timepoints = [0, *get_midnights(file_manager["base_dir"]), None]

    start, end = list(itertools.pairwise(target_timepoints))[day]
    if start is None:
        msg = f"No start time found for day {day}."
        raise ValueError(msg)

    if end:
        time_day_ends: int | None = _adjust_timepoint_for_daylight_savings(
            start,
            end,
            window_size,
        )
    else:
        time_day_ends = end
    return start, time_day_ends


def _adjust_timepoint_for_daylight_savings(
    start: int,
    end: int,
    window_size: int,
) -> int:
    """Adjusts the end timepoint for daylight savings time.

    Args:
        start: The start timepoint.
        end: The end timepoint.
        window_size: The size of the time window.

    Returns:
        int: The adjusted end timepoint.
    """
    day_length = end - start
    if (day_length + 1) // (3600 / window_size) == 25:  # noqa: PLR2004
        end = end - int(60 * 60 / window_size)
    if (day_length + 1) // (3600 / window_size) == 23:  # noqa: PLR2004
        end = end + int(60 * 60 / window_size)
    return end


def _extend_data(
    data: Any,  # noqa: ANN401
    extension: list[Any],
    action: str | None = None,
) -> list[Any]:
    """Extends the given data with the given extension using the specified action.

    Args:
        data: The data to be extended.
        extension: The extension to be added to the data.
        action: The action to be performed. Can be "prepend" or "append".
            Defaults to None.

    Returns:
        list: The extended data.
    """
    if action == "prepend":
        return extension + list(data)
    if action == "append":
        return list(data) + extension
    if action is not None:
        msg = f"Invalid action: {action}"
        raise ValueError(msg)
    return list(data)
