"""Command line interface for the actigraphy APP."""

import argparse
import logging
import pathlib
from typing import Any

from actigraphy.core import config

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME
logger = logging.getLogger(LOGGER_NAME)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        argparse.Namespace: The parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Actigraphy webapp to manually correct annotations for the sleep log diary."
        ),
        epilog="""Developed by the Child Mind Institute.""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input_folder", help="GGIR output folder.", type=pathlib.Path)
    parser.add_argument(
        "-v",
        "--verbosity",
        help="Logging verbosity, uses Python's logging module's logging levels.",
        type=int,
        default=20,
        choices=[10, 20, 30, 40, 50],
    )
    args = parser.parse_args()
    logger.debug("Parsed arguments:")
    for arg in vars(args):
        logger.debug("  %s = %s", arg, _add_string_quotation(getattr(args, arg)))
    return args


def get_subject_folders(args: argparse.Namespace) -> list[str]:
    """Returns a list of subject folders sorted by name.

    Args:
        args: The parsed command-line arguments.

    Returns:
        list[str]: A list of subject folders sorted by name.
    """
    input_datapath = args.input_folder
    return [
        str(directory)
        for directory in sorted(input_datapath.glob("output_*"))
        if directory.is_dir()
    ]


def _add_string_quotation(to_print: Any) -> str:  # noqa: ANN401
    """Adds quotation marks around a string or pathlib.Path object.

    Args:
        to_print: The object to add quotation marks to.

    Returns:
        Any: The object with quotation marks added, if it is a string or
            pathlib.Path object. Otherwise, the original object is returned.
    """
    if isinstance(to_print, str | pathlib.Path):
        return f'"{to_print}"'
    return str(to_print)
