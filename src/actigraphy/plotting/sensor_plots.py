"""Module for all plotting functions."""

import bisect
import datetime
import logging
from collections.abc import Sequence

import numpy as np
from plotly import graph_objects

from actigraphy.core import config, exceptions

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


def build_sensor_plot(
    timestamps: Sequence[datetime.datetime],
    sensor_angle: Sequence[float | int],
    sensor_acceleration: Sequence[float | int],
    title_day: str,
) -> tuple[graph_objects.Figure, int]:
    """Builds a plot of the sensor's angle and arm movement.

    Args:
        timestamps: The timestamps of the sensor's angle and arm movement.
        sensor_angle: The sensor's angle.
        sensor_acceleration: The arm movement.
        title_day: The title of the plot.
        n_ticks: The number of ticks on the x-axis.

    Returns:
        The plot.

    Notes:
        We assume that the delta time between timestamps is constant.
    """
    logger.debug("Building sensor plot.")
    _validate_timezones(timestamps)
    n_hours = _calculate_number_of_hours(timestamps)
    delta_time = timestamps[1] - timestamps[0]
    max_measurements = int(n_hours * 60 * 60 / delta_time.total_seconds())

    timestamp_values = _get_timestamp_x_values(timestamps, delta_time, max_measurements)
    x_min = 0.0
    x_max = n_hours * 60 * 60 / delta_time.total_seconds()
    x_tick_values, x_tick_names, x_hover_names = _get_x_axis(
        timestamps,
        n_hours,
        delta_time,
        max_measurements,
        (x_min, x_max),
    )
    x_hover_names = [x_hover_names[index] for index in timestamp_values]

    figure = _build_figure(
        sensor_angle,
        sensor_acceleration,
        title_day,
        timestamp_values,
        x_min,
        x_max,
        x_tick_values,
        x_tick_names,
        x_hover_names,
    )

    return figure, max_measurements


def add_rectangle(
    figure: graph_objects.Figure,
    limits: Sequence[float],
    color: str,
    label: str,
) -> graph_objects.Figure:
    """Adds a rectangle to the figure.

    Args:
        figure: The figure to add the rectangle to.
        limits: The limits of the rectangle in range [0, 1].
        color: The color of the rectangle.
        label: The label of the rectangle.
    """
    logger.debug("Adding rectangle to figure.")
    x_min = (figure.layout.xaxis.range[1] - figure.layout.xaxis.range[0]) * limits[
        0
    ] + figure.layout.xaxis.range[0]
    x_max = (figure.layout.xaxis.range[1] - figure.layout.xaxis.range[0]) * limits[
        1
    ] + figure.layout.xaxis.range[0]

    figure.add_vrect(
        x0=x_min,
        x1=x_max,
        fillcolor=color,
        opacity=0.2,
        annotation={"text": label},
    )
    return figure


def _validate_timezones(timestamps: Sequence[datetime.datetime]) -> None:
    """Validates that the timestamps contain no more than two different timezones."""
    logger.debug("Validating timezones.")
    timezones = {ts.tzinfo for ts in timestamps}
    if len(timezones) > 2:  # noqa: PLR2004
        msg = "More than two timezones in timestamps."
        raise exceptions.InternalError(msg)


def _calculate_number_of_hours(timestamps: Sequence[datetime.datetime]) -> float:
    """Calculates the number of hours in the graph."""
    logger.debug("Calculating number of hours.")
    timezones = list(dict.fromkeys(ts.tzinfo for ts in timestamps))
    max_timezones = 2
    if len(timezones) > max_timezones:
        msg = "More than two timezones in timestamps."
        raise exceptions.InternalError(msg)
    if len(timezones) == 2:  # noqa: PLR2004
        hour_difference = datetime.datetime(
            1,
            1,
            1,
            tzinfo=timezones[1],
        ) - datetime.datetime(1, 1, 1, tzinfo=timezones[0])
    if len(timezones) == 1:
        hour_difference = datetime.timedelta(hours=0)
    if len(timezones) == 0:
        msg = "No timezones in timestamps."
        raise exceptions.InternalError(msg)
    return 36 + (hour_difference.total_seconds() / 60 / 60)


def _get_timestamp_x_values(
    timestamps: Sequence[datetime.datetime],
    delta_time: datetime.timedelta,
    n_ticks: int,
) -> Sequence[int]:
    """Calculates the x values for the timestamps."""
    x_times = [
        datetime.datetime.combine(
            timestamps[0].date(),
            datetime.time(hour=12),
            tzinfo=timestamps[0].tzinfo,
        )
        + datetime.timedelta(seconds=delta_time.total_seconds() * tick)
        for tick in range(int(n_ticks))
    ]
    first_timestamp_index = min(
        range(len(x_times)),
        key=lambda i: abs(x_times[i] - timestamps[0]),
    )
    return list(
        range(
            first_timestamp_index,
            first_timestamp_index + len(timestamps),
        ),
    )


def _get_x_axis(
    timestamps: Sequence[datetime.datetime],
    n_hours: float,
    delta_time: datetime.timedelta,
    max_measurements: int,
    x_lim: tuple[float, float],
) -> tuple[list[float], list[str], list[str]]:
    """Calculate the x-axis tick values for a plot.

    Args:
        timestamps: List of x-axis timestamps.
        n_hours: Number of hours to plot.
        delta_time: Time interval between measurements.
        max_measurements: Maximum number of measurements.
        x_lim: Tuple representing the lower and upper limits of the x-axis.

    Returns:
        tuple: Tuple containing the x-axis tick values and names.
    """
    timestamps_including_missing: list[datetime.datetime] = [
        timestamps[0].replace(hour=12, minute=0, second=0, microsecond=0)
        + datetime.timedelta(seconds=delta_time.total_seconds() * tick)
        for tick in range(int(max_measurements))
    ]
    first_timestamp_index = bisect.bisect_left(
        timestamps_including_missing,
        timestamps[0],
    )

    timestamps_timezone_update = [
        timestamps_including_missing[first_timestamp_index + index].astimezone(
            timestamps[index].tzinfo,
        )
        for index in range(
            len(timestamps),
        )
    ]
    timestamps_including_missing[
        first_timestamp_index : first_timestamp_index
        + len(
            timestamps,
        )
    ] = timestamps_timezone_update

    timestamps_including_missing.append(
        timestamps_including_missing[-1] + datetime.timedelta(days=1),
    )

    x_tick_values = np.linspace(x_lim[0], x_lim[1], int(n_hours) + 1, dtype=int)

    x_tick_times = [timestamps_including_missing[tick] for tick in x_tick_values]
    x_tick_names = [
        datetime.datetime.strftime(
            time,
            "%H:%M",
        )
        if time.hour % 3 == 0
        else ""
        for time in x_tick_times
    ]
    n_timezones = len(list(dict.fromkeys(ts.tzinfo for ts in timestamps)))
    timezone_format = "%H:%M<br><b>%Z</b>"
    if n_timezones > 2:  # noqa: PLR2004
        msg = "More than two timezones in timestamps."
        raise exceptions.InternalError(msg)
    if n_timezones == 2:  # noqa: PLR2004
        x_tick_names[0] = datetime.datetime.strftime(x_tick_times[0], timezone_format)
        x_tick_names[-1] = datetime.datetime.strftime(x_tick_times[-1], timezone_format)

    x_hover_names = [
        datetime.datetime.strftime(
            time.astimezone(timestamps[0].tzinfo),
            timezone_format,
        )
        for time in timestamps_including_missing
    ]

    return x_tick_values.tolist(), x_tick_names, x_hover_names


def _build_figure(  # noqa: PLR0913
    sensor_angle: Sequence[float | int],
    sensor_acceleration: Sequence[float | int],
    title_day: str,
    timestamp_values: Sequence[int],
    x_min: float,
    x_max: float,
    x_tick_values: Sequence[float],
    x_tick_names: Sequence[str],
    x_hover_names: Sequence[str],
) -> graph_objects.Figure:
    """Build a figure for sensor plots.

    Args:
        sensor_angle: List of sensor angles.
        sensor_acceleration: List of sensor accelerations.
        title_day: Title for the figure.
        timestamp_values: List of timestamp values on the x-axis.
        x_min: Minimum x-axis value.
        x_max: Maximum x-axis value.
        x_tick_values: List of x-axis tick values.
        x_tick_names: List of x-axis tick names.
        x_hover_names: List of x-axis hover names.

    Returns:
        graph_objects.Figure: The built figure.
    """
    figure = graph_objects.Figure()
    figure.add_trace(
        graph_objects.Scatter(
            x=timestamp_values,
            y=sensor_angle,
            hovertemplate="<b>%{text}</b>",
            text=x_hover_names,
            mode="lines",
            name="Angle of sensor's z-axis",
            line_color="blue",
        ),
    )
    figure.add_trace(
        graph_objects.Scatter(
            x=timestamp_values,
            y=sensor_acceleration,
            hovertemplate="<b>%{text}</b>",
            text=x_hover_names,
            mode="lines",
            name="Arm movement",
            line_color="black",
        ),
    )

    figure.update_layout(
        {
            "title": title_day,
            "legend": {
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
            },
            "xaxis": {
                "tickmode": "array",
                "tickangle": 0,
                "range": [x_min, x_max],
                "tickvals": x_tick_values,
                "ticktext": x_tick_names,
            },
        },
    )

    return figure
