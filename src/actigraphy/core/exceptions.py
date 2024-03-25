"""Exceptions for actigraphy."""

import logging
from typing import Any

from actigraphy.core import config

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


class _AbstractError(Exception):
    """Base exception for all exceptions raised by actigraphy."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize a new instance of the AbstractException class.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        logger.error(*args, **kwargs)


class DatabaseError(_AbstractError):
    """Base exception for all database exceptions raised by actigraphy."""


class InternalError(_AbstractError):
    """Base exception for all internal exceptions raised by actigraphy."""
