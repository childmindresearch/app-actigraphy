"""This module contains the switches component for the Actigraphy app.

The switches component contains three BooleanSwitch components for use in the
Actigraphy app. The first switch is used to indicate whether the participant
has multiple sleep periods in a 24-hour period. The second switch is used to
indicate whether the participant has more than 2 hours of missing sleep data.
The third switch is used to indicate whether the user needs to review the sleep
data for a particular night.
"""

import logging

import dash
import dash_bootstrap_components as dbc
import dash_daq
from dash import html

from actigraphy.core import callback_manager, config
from actigraphy.database import crud, database
from actigraphy.io import ggir_files

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


def switches() -> html.Div:
    """Returns a Dash HTML div containing three BooleanSwitch components.

    - The first switch is used to indicate whether the participant has multiple
        sleep periods in a 24-hour period.
    - The second switch is used to indicate whether the participant has more
        than 2 hours of missing sleep data from 8PM to 8AM.
    - The third switch is used to indicate whether the user needs to
        review the sleep data for a particular night.

    Returns:
        html.Div: A Dash HTML div containing three BooleanSwitch components.
    """
    # pylint: disable=not-callable because dash_daq.BooleanSwitch is callable
    return html.Div(
        children=[
            dbc.Row(
                [
                    dbc.Col(
                        dash_daq.BooleanSwitch(
                            id="multiple_sleep",
                            on=False,
                            label=" Are there multiple sleep periods in these data?",
                            className="switches-col",
                        ),
                    ),
                    dbc.Col(
                        dash_daq.BooleanSwitch(
                            id="review_night",
                            on=False,
                            label=" Do you need to review this night?",
                            className="switches-col",
                        ),
                    ),
                    dbc.Col(
                        dash_daq.BooleanSwitch(
                            id="exclude_night",
                            on=False,
                            label=" Are >2 hours of data missing between 8PM to 8AM?",
                            className="switches-col",
                        ),
                    ),
                ],
            ),
            html.Div(id="null-data-sleep"),
            html.Div(id="null-data-night"),
            html.Div(id="null-data-review"),
        ],
    )


@callback_manager.global_manager.callback(
    dash.Output("multiple_sleep", "on"),
    dash.Output("exclude_night", "on"),
    dash.Output("review_night", "on"),
    dash.Input("day_slider", "value"),
    dash.State("file_manager", "data"),
)
def update_switches(day: int, file_manager: dict[str, str]) -> tuple[bool, bool, bool]:
    """Reads the sleep logs for the given day.

    Args:
        day: The day for which to retrieve the sleep logs.
        file_manager: A dictionary containing file paths for various sleep log
            files.

    Returns:
        tuple[bool, bool, bool]: A tuple of boolean values indicating whether
            there are naps, missing sleep, and reviewed nights for the given
            day.
    """
    logger.debug("Entering update switches callback")
    session = next(database.session_generator(file_manager["database"]))
    day_model = crud.read_day_by_subject(session, day, file_manager["identifier"])
    return (
        day_model.is_multiple_sleep,
        day_model.is_missing_sleep,
        day_model.is_reviewed,
    )


@callback_manager.global_manager.callback(
    dash.Output("null-data-night", "children"),
    dash.Input("exclude_night", "on"),
    dash.State("day_slider", "value"),
    dash.State("file_manager", "data"),
    prevent_initial_call=True,
)
def toggle_exclude_night(
    exclude_button: bool,  # noqa: FBT001
    day_index: int,
    file_manager: dict[str, str],
) -> None:
    """Toggles the exclusion of a night in the missing sleep file.

    Args:
        exclude_button: Whether to exclude the night or not.
        day_index : The day to toggle the exclusion for.
        file_manager: A dictionary containing file paths for the missing sleep file.
    """
    _toggle_bool_field(day_index, "is_missing_sleep", exclude_button, file_manager)
    ggir_files.write_data_cleaning(file_manager)


@callback_manager.global_manager.callback(
    dash.Output("null-data-review", "children"),
    dash.Input("review_night", "on"),
    dash.State("day_slider", "value"),
    dash.State("file_manager", "data"),
    prevent_initial_call=True,
)
def toggle_review_night(
    review_night: bool,  # noqa: FBT001
    day_index: int,
    file_manager: dict[str, str],
) -> None:
    """Toggles the review night flag for a given day in the review night file.

    Args:
        review_night: The new review night flag value (0 or 1).
        day_index: The day index to toggle the flag for.
        file_manager: A dictionary containing file paths for the review night file.
    """
    _toggle_bool_field(day_index, "is_reviewed", review_night, file_manager)


@callback_manager.global_manager.callback(
    dash.Output("null-data-sleep", "children"),
    dash.Input("multiple_sleep", "on"),
    dash.State("day_slider", "value"),
    dash.State("file_manager", "data"),
    prevent_initial_call=True,
)
def toggle_nap(
    multiple_sleep: bool,  # noqa: FBT001
    day_index: int,
    file_manager: dict[str, str],
) -> None:
    """Toggles the nap status for a given day in the multiple sleep log file.

    Args:
        multiple_sleep: The new nap status for the given day.
        day_index: The day to toggle the nap status for.
        file_manager: A dictionary containing file paths for various files.
    """
    _toggle_bool_field(day_index, "is_multiple_sleep", multiple_sleep, file_manager)


def _toggle_bool_field(
    day_index: int,
    fieldname: str,
    value: bool,  # noqa: FBT001
    file_manager: dict[str, str],
) -> None:
    """Toggles a boolean field for a given day.

    Args:
        day_index: The day to toggle the field for.
        fieldname: The name of the field to toggle.
        value: The new value of the field.
        file_manager: A dictionary containing file paths for various files.
    """
    session = next(database.session_generator(file_manager["database"]))
    day = crud.read_day_by_subject(session, day_index, file_manager["identifier"])
    setattr(day, fieldname, value)
    session.commit()
