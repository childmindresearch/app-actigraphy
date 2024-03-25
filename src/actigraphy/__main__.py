"""Entrypoints for the Actigraphy app."""

import logging

from actigraphy import app
from actigraphy.core import config
from actigraphy.io import preprocess


def main_entrypoint() -> None:
    """Creates the Dash app and runs the server."""
    dash_app = app.create_app()
    dash_app.run_server(port=8051, host="0.0.0.0")  # noqa: S104


def preprocess_entrypoint() -> None:
    """Entrypoint for pre-processing the data."""
    config.initialize_logger(logging_level=logging.DEBUG)
    preprocess.run()


if __name__ == "__main__":
    main_entrypoint()
