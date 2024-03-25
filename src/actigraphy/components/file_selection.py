"""Contains the file selection component of the Actigraphy app.

The file selection component contains an input box for the evaluator's name, and
dropdown menu for selecting a subject.
"""

import logging

import dash
import dash_bootstrap_components
from dash import dcc, html

from actigraphy.components import day_slider, finished_checkbox, graph, switches
from actigraphy.core import callback_manager, config, exceptions
from actigraphy.core import utils as core_utils
from actigraphy.database import crud, database
from actigraphy.database import utils as database_utils

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


def file_selection(dropdown_choices: list[str]) -> html.Div:
    """Create a file selection Dash HTML div.

    Contains an input box for the evaluator's name, a dropdown menu for
    selecting a subject, and a spinner for indicating loading.

    Args:
        dropdown_choices: A list of choices for the dropdown menu.

    Returns:
        html.Div: A Dash HTML div containing the input box, dropdown menu, and
            spinner.
    """
    drop_down = dcc.Dropdown(
        dropdown_choices,
        dropdown_choices[0],
        id="my-dropdown",
    )
    loading_text = html.Div(
        [
            html.P(
                """Please be aware that the initial loading of a subject might
                require some time as we convert the data into a SQLite database
                format. Once this process is complete, future accesses will
                directly utilize this database, ensuring quicker data
                retrieval.""",
            ),
        ],
    )
    spinner = html.Div(
        [
            dash_bootstrap_components.Spinner(html.Div(id="loading")),
        ],
        style={"margin": "40px 0"},
    )

    confirmation_button = html.Button(
        "Load Files",
        id="load_file_button",
        n_clicks=0,
        style={"margin": 10},
    )

    return html.Div(
        [
            drop_down,
            loading_text,
            confirmation_button,
            spinner,
        ],
        style={"padding": 10},
    )


@callback_manager.global_manager.callback(
    [
        dash.Output("annotations-data", "children"),
        dash.Output("loading", "children"),
        dash.Output("file_manager", "data"),
    ],
    dash.Input("load_file_button", "n_clicks"),
    dash.State("my-dropdown", "value"),
    prevent_initial_call=True,
)
def parse_files(
    n_clicks: int,  # pylint: disable=unused-argument n_clicks intentionally unused.  # noqa: ARG001
    filepath: str,
) -> tuple[list[html.Div], str, dict[str, str]]:
    """Parses the contents of the selected files and returns the UI components.

    Args:
        n_clicks: The number of times the parse button has been clicked. Used to trigger
            the callback.
        filepath: The path to the selected file.

    Returns:
        tuple: A tuple containing the UI components to be displayed, an empty
        string, a boolean indicating whether parsing was successful, and the
        file manager object.

    Notes:
        The last day is not shown in the UI, as all 36 hour windows are
        referenced by their first day.
    """
    logger.debug("Parsing files...")
    file_manager = core_utils.FileManager(base_dir=filepath).__dict__

    logger.info("Creating/loading database")
    database.Database(file_manager["database"]).create_database()

    session = next(database.session_generator(file_manager["database"]))
    try:
        subject = crud.read_subject(session, file_manager["identifier"])
    except exceptions.DatabaseError:
        logger.info("Subject not found in database. Creating new subject.")
        subject = database_utils.initialize_subject(
            file_manager["identifier"],
            file_manager["metadata_file"],
            file_manager["ms4_file"],
            session,
        )

    ui_components = [
        day_slider.day_slider(file_manager["identifier"], len(subject.days) - 1),
        finished_checkbox.finished_checkbox(),
        switches.switches(),
        graph.graph(),
    ]
    return (
        ui_components,
        "",
        file_manager,
    )
