"""Dash HTML div for a slider component for selecting days."""

import datetime
import itertools
import logging
import uuid

import dash
from dash import dcc, html

from actigraphy.components import utils
from actigraphy.core import callback_manager, config
from actigraphy.database import crud, database

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME
logger = logging.getLogger(LOGGER_NAME)


def day_slider(participant_name: str, max_count: int) -> html.Div:
    """A slider component for selecting a day for a participant.

    Args:
        participant_name : The name of the participant.
        max_count: The maximum number of days available for selection.

    Returns:
        html.Div: A Dash HTML div containing a slider component for selecting a
            day for a participant.

    Notes:
        The frontend shows 1-indexed days, but the backend uses 0-indexed days.
    """
    return html.Div(
        children=[
            html.B(
                "* All changes will be automatically saved\n\n",
                style={"color": "red"},
            ),
            html.B(f"Select day for participant {participant_name}:"),
            dcc.Slider(
                0,
                max_count - 1,
                1,
                marks={f"{i}": f"{i + 1}" for i in range(max_count)},
                value=0,
                id="day_slider",
            ),
            html.Div(id="daylight_savings_timepoint"),
            html.Div(id="daylight_savings_shift"),
            html.Div(id="trigger_day_load"),
        ],
        style={"margin-left": "20px", "padding": 10},
    )


@callback_manager.global_manager.callback(
    [
        dash.Output("daylight_savings_timepoint", "value"),
        dash.Output("daylight_savings_shift", "value"),
        dash.Output("trigger_day_load", "value"),
    ],
    dash.Input("day_slider", "value"),
    dash.State("file_manager", "data"),
)
def update_daylight_savings(
    day_index: int,
    file_manager: dict[str, str],
) -> tuple[str | None, int | None, str]:
    """Update the daylight savings time data.

    Args:
        day_index: The index of the day to use.
        file_manager: A dictionary containing file paths.

    Returns:
        int: The index of the first data point that is affected by daylight
            savings time.

    Notes:
        The trigger_day_load output is solely used to trigger other callbacks.
        It is set to a UUID to ensure that it is always unique, and we don't
        have to consider the previous value.
    """
    logger.debug("Updating daylight savings time data")
    session = next(database.session_generator(file_manager["database"]))
    day_data = utils.get_day_data(
        day_index,
        file_manager["database"],
        file_manager["identifier"],
    )
    day_model = crud.read_day_by_subject(session, day_index, file_manager["identifier"])
    times_of_interest = [
        data_point
        for data_point in day_data
        if (
            data_point.timestamp.date() == day_model.date
            and data_point.timestamp.hour >= 12  # noqa: PLR2004
        )
        or (data_point.timestamp.date() == day_model.date + datetime.timedelta(days=1))
    ]
    n_timezones = len(
        {data_point.timestamp_utc_offset for data_point in times_of_interest},
    )
    if n_timezones == 1:
        return None, None, uuid.uuid4().hex

    daylight_saving_differences = [
        time_1.timestamp_utc_offset - time_2.timestamp_utc_offset
        for time_1, time_2 in itertools.pairwise(times_of_interest)
    ]
    daylight_saving_shift = next(
        (diff for diff in daylight_saving_differences if diff != 0),
    )
    daylight_saving_index = daylight_saving_differences.index(daylight_saving_shift)
    daylight_saving_timestamp = times_of_interest[
        daylight_saving_index
    ].timestamp_with_tz

    trigger_load = uuid.uuid4().hex
    return str(daylight_saving_timestamp), daylight_saving_shift, trigger_load
