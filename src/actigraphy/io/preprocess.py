"""Module for preprocessing actigraphy data."""

import argparse
import logging
import pathlib

from actigraphy.core import config
from actigraphy.core import utils as core_utils
from actigraphy.database import database
from actigraphy.database import utils as database_utils

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Preprocess actigraphy data.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data-dir",
        type=pathlib.Path,
        default=pathlib.Path("/data"),
        help="Path to the data directory.",
    )
    parser.add_argument(
        "--identifier",
        type=str,
        default="",
        help="""The identifier for the participant. If not provided, all participants
          will be processed.""",
    )
    return parser.parse_args()


def run() -> None:
    """Run the preprocessing."""
    args = parse_args()

    if not args.identifier:
        logger.info("Processing all participants")
        subject_dirs = tuple(args.data_dir.glob("output_*"))
        if len(subject_dirs) == 0:
            logger.warning("No participants found, exiting.")
            return
    else:
        subject_dirs = (args.data_dir / args.identifier,)

    for subject_dir in subject_dirs:
        logger.info("Processing %s", subject_dir)

        if not subject_dir.is_dir():
            logger.warning("%s is not a directory, skipping.", subject_dir)
            continue

        file_manager = core_utils.FileManager(subject_dir)
        if pathlib.Path(file_manager.database).exists():
            logger.info("Subject already processed, skipping.")
            continue

        logger.info("Creating database.")
        create_subject_database(file_manager)
        logger.info("Finished processing %s", subject_dir)


def create_subject_database(file_manager: core_utils.FileManager) -> None:
    """Creates a subject database.

    Args:
        file_manager: The file manager object containing the necessary files.

    """
    database.Database(file_manager.database).create_database()
    session = next(database.session_generator(file_manager.database))
    database_utils.initialize_subject(
        file_manager.identifier,
        file_manager.metadata_file,
        file_manager.ms4_file,
        session,
    )
