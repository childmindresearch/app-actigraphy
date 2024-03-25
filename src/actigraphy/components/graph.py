"""Defines the graph component of the Actigraphy app.

The graph component contains a graph range sliders for use in the Actigraphy
app. The graph displays the sensor angle and arm movement data for a given day.
The range slider is used to select a sleep window for the given day.
"""

import datetime
import json
import logging
import statistics
from collections.abc import Sequence

import dash
from dash import dash_table, dcc, html
from plotly import graph_objects

from actigraphy.components import utils as components_utils
from actigraphy.core import callback_manager, config
from actigraphy.core import utils as core_utils
from actigraphy.database import crud, database, models
from actigraphy.database import utils as database_utils
from actigraphy.io import ggir_files
from actigraphy.plotting import sensor_plots

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME
TIME_FORMATTING = settings.TIME_FORMATTING
N_SLIDER_STEPS = settings.N_SLIDER_STEPS
DEFAULT_SLEEP_TIME = settings.DEFAULT_SLEEP_TIME

logger = logging.getLogger(LOGGER_NAME)


def graph() -> html.Div:
    """Builds the graph component of the Actigraphy app.

    Returns:
        html.Div: A Dash HTML div containing a graph and range slider
        components.
    """
    return html.Div(
        children=[
            dcc.Graph(id="graph", style={"marginBottom": "-3rem"}),
            html.Div(
                children=[],
                id="slider_div",
                style={
                    "marginLeft": "55px",
                    "marginRight": "55px",
                },
            ),
            html.Div(
                children=[
                    html.Button(
                        "Add Slider",
                        id="add_slider",
                        style={"marginRight": "10px", "zIndex": "1"},
                    ),
                    html.Button(
                        "Remove Slider",
                        id="remove_slider",
                        style={"zIndex": "1"},
                    ),
                ],
                style={
                    "marginLeft": "55px",
                    "marginRight": "55px",
                    "marginBottom": "10px",
                    "display": "flex",
                },
            ),
            html.Div(
                style={
                    "marginLeft": "55px",
                    "marginRight": "55px",
                    "marginTop": "20px",
                },
                children=[
                    html.P("GGIR Time:"),
                    dash_table.DataTable(
                        data=[],
                        id="ggir_window_table",
                        columns=[
                            {"name": "Sleep Onset", "id": "ggir_onset"},
                            {"name": "Sleep Offset", "id": "ggir_wakeup"},
                            {"name": "Sleep Duration", "id": "ggir_duration"},
                        ],
                        sort_action="native",
                        sort_mode="multi",
                        column_selectable="single",
                    ),
                ],
            ),
            html.Div(
                style={
                    "marginLeft": "55px",
                    "marginRight": "55px",
                },
                children=[
                    html.P("Sleep Times:"),
                    dash_table.DataTable(
                        data=[],
                        id="sleep_window_table",
                        columns=[
                            {"name": "Sleep Onset", "id": "onset"},
                            {"name": "Sleep Offset", "id": "wakeup"},
                            {"name": "Sleep Duration", "id": "duration"},
                        ],
                        sort_action="native",
                        sort_mode="multi",
                        column_selectable="single",
                    ),
                ],
            ),
        ],
    )


@callback_manager.global_manager.callback(
    dash.Output("graph", "figure"),
    dash.Input("trigger_day_load", "value"),
    dash.Input({"type": "range_slider", "index": dash.ALL}, "value"),
    dash.State("day_slider", "value"),
    dash.State("file_manager", "data"),
    prevent_initial_call=True,
)
def create_graph(
    _trigger_load: str,
    drag_values: tuple[list[int]],
    day_index: int,
    file_manager: dict[str, str],
) -> graph_objects.Figure:
    """Creates a graph for a given day using data from the file manager."""
    logger.debug("Creating graph.")
    session = next(database.session_generator(file_manager["database"]))
    subject = crud.read_subject(session, file_manager["identifier"])
    dates = [day.date for day in subject.days]

    logger.debug("Getting day data.")
    data_points = components_utils.get_day_data(
        day_index,
        file_manager["database"],
        file_manager["identifier"],
    )
    included_data_points = [
        point
        for point in data_points
        if (
            point.timestamp_with_tz.date() == dates[day_index]
            and point.timestamp_with_tz.hour >= 12  # noqa: PLR2004
        )
        or point.timestamp_with_tz.date()
        == dates[day_index] + datetime.timedelta(days=1)
    ]

    logger.debug("Getting non-wear data.")
    timestamps = [point.timestamp_with_tz for point in included_data_points]
    sensor_angle = [point.sensor_angle for point in included_data_points]
    arm_movement = [point.sensor_acceleration for point in included_data_points]
    non_wear = [point.non_wear for point in included_data_points]

    title_day = (
        f"Day {day_index+1}:"
        f"{included_data_points[0].timestamp.strftime('%A, %d %B %Y')}"
    )  # Frontend uses 1-indexed days.

    return _build_figure(
        timestamps,
        sensor_angle,
        arm_movement,
        title_day,
        drag_values,
        non_wear,
    )


@callback_manager.global_manager.callback(
    dash.Output("slider_div", "children", allow_duplicate=True),
    dash.Output("sleep_window_table", "data", allow_duplicate=True),
    dash.Output("ggir_window_table", "data"),
    dash.Input("trigger_day_load", "value"),
    dash.State("day_slider", "value"),
    dash.State("file_manager", "data"),
    dash.State("daylight_savings_shift", "value"),
    prevent_initial_call=True,
)
def refresh_range_slider(
    _trigger_load: str,
    day_index: int,
    file_manager: dict[str, str],
    daylight_savings_shift: int | None,
) -> tuple[list[int], list[dict[str, str]], list[dict[str, str]]]:
    """Reads the sleep logs for the given day.

    Args:
        _trigger_load: A trigger for the callback.
        day_index: The day for which to retrieve the sleep logs.
        file_manager: A dictionary containing file paths for various sleep log
            files.
        daylight_savings_shift: The seconds offset due to daylight savings.
        slider_index: The index of the slider to refresh.

    Returns:
        list[int]: A list containing the sleep onset and sleep offset points.
    """
    session = next(database.session_generator(file_manager["database"]))
    day = crud.read_day_by_subject(session, day_index, file_manager["identifier"])

    sliders = []
    data_table: list[dict[str, str]] = []
    for index in range(len(day.sleep_times)):
        sleep_time = day.sleep_times[index].onset_with_tz
        wake_time = day.sleep_times[index].wakeup_with_tz

        sleep_point = core_utils.time2point(
            sleep_time,
            day.date,
            daylight_savings_shift,
        )
        wake_point = core_utils.time2point(
            wake_time,
            day.date,
            daylight_savings_shift,
        )
        sliders.append(
            _create_slider(
                index,
                day.sleep_times[index].id,
                (sleep_point, wake_point),
            ),
        )

        data_table.append(
            {
                "onset": sleep_time.strftime(TIME_FORMATTING),
                "wakeup": wake_time.strftime(TIME_FORMATTING),
                "duration": str(wake_time - sleep_time),
            },
        )

    if day.ggir_sleep_times:
        ggir_time = [
            {
                "ggir_onset": day.ggir_sleep_times[0].onset_with_tz.strftime(
                    TIME_FORMATTING,
                ),
                "ggir_wakeup": day.ggir_sleep_times[0].wakeup_with_tz.strftime(
                    TIME_FORMATTING,
                ),
                "ggir_duration": str(
                    day.ggir_sleep_times[0].wakeup_with_tz
                    - day.ggir_sleep_times[0].onset_with_tz,
                ),
            },
        ]
    else:
        ggir_time = [{}]

    return sliders, data_table, ggir_time


@callback_manager.global_manager.callback(
    dash.Output(
        {"type": "range_slider", "index": dash.ALL},
        "value",
        allow_duplicate=True,
    ),
    dash.Output("sleep_window_table", "data", allow_duplicate=True),
    dash.Input(
        {
            "type": "range_slider",
            "index": dash.ALL,
        },
        "value",
    ),
    dash.State({"type": "slider_pk", "index": dash.ALL}, "children"),
    dash.State("file_manager", "data"),
    dash.State("day_slider", "value"),
    dash.State("daylight_savings_timepoint", "value"),
    dash.State("daylight_savings_shift", "value"),
    prevent_initial_call=True,
)
def adjust_range_slider(  # noqa: PLR0913
    drag_values: list[list[int]],
    primary_keys: list[int],
    file_manager: dict[str, str],
    day_index: int,
    daylight_savings_timepoint: str | None,
    daylight_savings_shift: int | None,
) -> tuple[list[list[int]], dash.Patch]:
    """Checks if the new position is valid and writes the sleep log to a file.

    If the new position is not valid, the callback will return the state to
    the previous position.

    Args:
        drag_values: The drag values of the range sliders.
        primary_keys: The primary keys of the sleep log.
        file_manager: The file manager containing the sleep log.
        day_index: The day for which to adjust the range slider.
        daylight_savings_timepoint: The index of the first data point that is
            affected by daylight savings time.
        daylight_savings_shift: The seconds offset due to daylight savings.
        other_drag_values: The drag values of the other range sliders.

    Notes:
        This assumes only one side of the slider is being dragged at a time.
        It could break if the second side is dragged before the first side is
        processed.
    """
    logger.debug("Adjusting range slider.")

    input_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
    if not input_id:
        return drag_values, dash.no_update
    caller_index = json.loads(input_id)["index"]

    caller_drag_values = drag_values[caller_index]
    other_drag_values = [
        *drag_values[:caller_index],
        *drag_values[caller_index + 1 :],
    ]

    new_caller_values = _adjust_range_slider_values(
        caller_drag_values,
        other_drag_values,
    )

    session = next(database.session_generator(file_manager["database"]))
    day = crud.read_day_by_subject(session, day_index, file_manager["identifier"])

    first_data_point = components_utils.get_day_data(
        day_index,
        file_manager["database"],
        file_manager["identifier"],
    )[0]
    base_timezone = first_data_point.timestamp_utc_offset

    sleep_time = core_utils.point2time(
        new_caller_values[0],
        day.date,
        base_timezone,
        daylight_savings_timepoint,
        daylight_savings_shift,
    )
    wake_time = core_utils.point2time(
        new_caller_values[1],
        day.date,
        base_timezone,
        daylight_savings_timepoint,
        daylight_savings_shift,
    )

    data_index = next(
        index
        for index, point in enumerate(day.sleep_times)
        if point.id == int(primary_keys[caller_index])
    )

    day.sleep_times[data_index].onset = sleep_time.astimezone(datetime.UTC)
    day.sleep_times[
        data_index
    ].onset_utc_offset = sleep_time.utcoffset().total_seconds()  # type: ignore [union-attr]
    day.sleep_times[data_index].wakeup = wake_time.astimezone(datetime.UTC)
    day.sleep_times[
        data_index
    ].wakeup_utc_offset = wake_time.utcoffset().total_seconds()  # type: ignore [union-attr]

    new_values = other_drag_values
    new_values.insert(caller_index, new_caller_values)

    patch_table = dash.Patch()
    patch_table[caller_index] = {
        "onset": sleep_time.strftime(TIME_FORMATTING),
        "wakeup": wake_time.strftime(TIME_FORMATTING),
        "duration": str(wake_time - sleep_time),
    }

    session.commit()
    ggir_files.write_sleeplog(file_manager)
    ggir_files.write_all_sleep_times(file_manager)

    return new_values, patch_table


@callback_manager.global_manager.callback(
    dash.Output("slider_div", "children", allow_duplicate=True),
    dash.Output("sleep_window_table", "data", allow_duplicate=True),
    dash.Input("add_slider", "n_clicks"),
    dash.State("file_manager", "data"),
    dash.State("day_slider", "value"),
    dash.State("slider_div", "children"),
    prevent_initial_call=True,
)
def add_sliders(
    n_clicks: int,  # noqa: ARG001
    file_manager: dict[str, str],
    day_index: int,
    sliders: list[html.Div],
) -> dash.Patch:
    """Adds sliders from the graph.

    Args:
        n_clicks: The number of times the add button has been clicked.
        file_manager: The file manager containing the file locations.
        day_index: The index of the day for which to add a slider.
        sliders: The slider div containing the sliders.

    Returns:
        dash.Patch: A patch to add a slider.
    """
    logger.debug("Adding slider %s.", len(sliders))
    session = next(database.session_generator(file_manager["database"]))
    day = crud.read_day_by_subject(session, day_index, file_manager["identifier"])
    default_sleep = datetime.datetime.combine(day.date, DEFAULT_SLEEP_TIME)
    nearest_data_point = database_utils.find_closest_datapoint(
        default_sleep,
        session,
    )
    new_sleep_time = models.SleepTime(
        onset=default_sleep,
        onset_utc_offset=nearest_data_point.timestamp_utc_offset,
        wakeup=default_sleep,
        wakeup_utc_offset=nearest_data_point.timestamp_utc_offset,
    )
    day.sleep_times.append(new_sleep_time)
    session.commit()

    slider_points = core_utils.time2point(
        default_sleep,
        day.date,
        nearest_data_point.timestamp_utc_offset,
    )
    patch_slider = dash.Patch()
    slider = _create_slider(
        index=len(sliders),
        primary_key=new_sleep_time.id,
        values=(slider_points, slider_points),
    )
    patch_slider.append(slider)

    default_sleep_tz = default_sleep.replace(
        tzinfo=datetime.timezone(
            offset=datetime.timedelta(seconds=nearest_data_point.timestamp_utc_offset),
        ),
    )
    patch_table = dash.Patch()
    patch_table.append(
        {
            "onset": default_sleep_tz.strftime(TIME_FORMATTING),
            "wakeup": default_sleep_tz.strftime(TIME_FORMATTING),
            "duration": str(datetime.timedelta()),
        },
    )

    # Rewrite data cleaning as it has a special case for no sliders.
    ggir_files.write_data_cleaning(file_manager)
    return patch_slider, patch_table


@callback_manager.global_manager.callback(
    dash.Output("slider_div", "children", allow_duplicate=True),
    dash.Output("sleep_window_table", "data", allow_duplicate=True),
    dash.Input("remove_slider", "n_clicks"),
    dash.State("slider_div", "children"),
    dash.State("file_manager", "data"),
    prevent_initial_call=True,
)
def remove_sliders(
    remove_clicks: int,  # noqa: ARG001
    slider_div: list[html.Div],
    file_manager: dict[str, str],
) -> dash.Patch:
    """Removes sliders from the graph.

    Args:
        remove_clicks: The number of times the remove button has been clicked.
        slider_div: The slider div containing the sliders.
        file_manager: The file manager containing the file locations.

    Returns:
        dash.Patch: A patch to remove the last slider.

    """
    logger.debug("Removing slider.")
    primary_key = slider_div[-1]["props"]["children"][0]["props"]["children"]
    session = next(database.session_generator(file_manager["database"]))
    sleep_time = session.query(models.SleepTime).filter_by(id=primary_key).first()
    session.delete(sleep_time)

    patch_slider = dash.Patch()
    del patch_slider[-1]

    patch_table = dash.Patch()
    del patch_table[-1]

    session.commit()
    # Rewrite data cleaning as it has a special case for no sliders.
    ggir_files.write_data_cleaning(file_manager)
    return patch_slider, patch_table


def _build_figure(  # noqa: PLR0913
    timestamps: list[datetime.datetime],
    sensor_angle: list[float],
    arm_movement: list[float],
    title_day: str,
    drag_values: tuple[list[int]],
    nonwear_changes: list[bool],
) -> graph_objects.Figure:
    """Build the graph figure."""
    logger.debug("Building figure.")
    rescale_arm_movement = [value * 50 - 210 for value in arm_movement]
    figure, max_measurements = sensor_plots.build_sensor_plot(
        timestamps,
        sensor_angle,
        rescale_arm_movement,
        title_day,
    )

    for values in drag_values:
        if not values:
            continue
        drag_fraction = [value / N_SLIDER_STEPS for value in values]
        sensor_plots.add_rectangle(figure, drag_fraction, "red", "sleep window")

    continuous_non_wear_blocks = _find_continuous_blocks(nonwear_changes)
    non_wear_fractions = [
        value / max_measurements for value in continuous_non_wear_blocks
    ]
    all_timepoints_included = len(timestamps) == max_measurements
    if not all_timepoints_included:
        includes_start = timestamps[0].hour == 12 and timestamps[0].minute == 0  # noqa: PLR2004
        if not includes_start:
            offset = 1 - len(timestamps) / max_measurements
            non_wear_fractions = [fraction + offset for fraction in non_wear_fractions]

    for index in range(0, len(non_wear_fractions), 2):
        sensor_plots.add_rectangle(
            figure,
            [
                non_wear_fractions[index],
                non_wear_fractions[index + 1],
            ],
            "green",
            "non-wear",
        )
    return figure


def _find_continuous_blocks(vector: Sequence[bool]) -> list[int]:
    """Finds the indices of continuous blocks of True values in a vector.

    Args:
        vector: The vector to search.

    Returns:
        list[int]: A list of indices of continuous blocks of True values in the
            vector.
    """
    return [
        index
        for index, value in enumerate(vector)
        if value
        and (
            index == 0
            or index == len(vector) - 1
            or not vector[index - 1]
            or not vector[index + 1]
        )
    ]


def _create_slider(
    index: int,
    primary_key: int,
    values: tuple[int, int] = (0, 0),
) -> html.Div:
    """Creates slider components for selecting sleep windows.

    Args:
        index: The index of the slider.
        primary_key: The primary key of the sleep log.
        values: The initial values of the slider.

    Returns:
        A list of slider components.
    """
    return html.Div(
        id={"type": "slider_div", "index": index},
        children=[
            html.P(
                str(primary_key),
                style={"display": "none"},
                id={"type": "slider_pk", "index": index},
            ),
            dcc.RangeSlider(
                min=0,
                max=N_SLIDER_STEPS,
                step=1,
                marks=None,
                id={"type": "range_slider", "index": index},
                updatemode="mouseup",
                value=values,
            ),
        ],
    )


def _adjust_range_slider_values(
    drag_values: list[int],
    other_drag_values: list[list[int]],
) -> list[int]:
    """Adjusts the range slider values to ensure validity.

    Slider ranges are not allowed to intersect with each other.

    Args:
        drag_values: The drag values of the range slider.
        other_drag_values: The drag values of the other range sliders.

    Returns:
        list[int]: The adjusted range slider values.
    """
    if not drag_values:
        return drag_values

    new_values = [drag_values[0], drag_values[1]]
    n_loops = 0
    max_loops = 100
    start_values: list[int | None] = [None, None]

    while new_values != start_values:
        n_loops += 1
        start_values = [new_values[0], new_values[1]]
        for other in other_drag_values:
            if not other:
                continue
            this_on_right_of_other = statistics.mean(drag_values) > statistics.mean(
                other,
            )
            if other[0] <= new_values[0] <= other[1]:
                new_values[0] = other[1] + 1 if this_on_right_of_other else other[0] - 1

            if other[0] <= new_values[1] <= other[1]:
                new_values[1] = other[1] + 1 if this_on_right_of_other else other[0] - 1

            if new_values[0] <= other[0] and new_values[1] >= other[1]:
                if this_on_right_of_other:
                    new_values[0] = other[1] + 1
                else:
                    new_values[1] = other[0] - 1

        if n_loops > max_loops:
            msg = "Infinite loop detected."
            raise RuntimeError(msg)

    return new_values
