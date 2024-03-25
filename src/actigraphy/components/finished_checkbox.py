"""Defines a Dash checklist component.

The checklist allows the user to indicate whether they are done with the
current participant and would like to proceed to the next one.
"""

import logging

import dash
from dash import dcc

from actigraphy.core import callback_manager, config
from actigraphy.database import crud, database

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


def finished_checkbox() -> dcc.Checklist:
    """Create a Dash checklist component.

    This checklist allows the user to indicate whether they are done with the
    current participant and would like to proceed to the next one.

    Returns:
        dcc.Checklist: A Dash checklist component with a single checkbox option.
    """
    return dcc.Checklist(
        [" I'm done and I would like to proceed to the next participant. "],
        id="are-you-done",
        style={"margin-left": "50px"},
    )


@callback_manager.global_manager.callback(
    dash.Output("check-done", "children"),
    dash.Input("are-you-done", "value"),
    dash.State("file_manager", "data"),
)
def write_log_done(is_user_done: str, file_manager: dict[str, str]) -> bool:
    """Writes a log message indicating that the analysis has been completed.

    Args:
        is_user_done: If true, the text of the checkbox, otherwise empty string.
        file_manager: A dictionary containing information about the file being analyzed.
    """
    logger.debug("Entering write log done callback")
    session = next(database.session_generator(file_manager["database"]))
    subject = crud.read_subject(session, file_manager["identifier"])

    is_done = bool(is_user_done)
    subject.is_finished = is_done
    session.commit()

    return is_done
