"""Contains the app settings."""

import datetime
import functools
import logging

import pydantic
import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    """Represents the app settings."""

    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix="ACTIGRAPHY_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    APP_NAME: str = pydantic.Field(
        "Actigraphy",
        description="The name of the app.",
        json_schema_extra={
            "env": "APP_NAME",
        },
    )
    LOGGER_NAME: str = pydantic.Field(
        "Actigraphy",
        description="The name of the logger.",
        json_schema_extra={
            "env": "LOGGER_NAME",
        },
    )

    DEFAULT_SLEEP_TIME: datetime.time = pydantic.Field(
        datetime.time(12, 0, 0),
        description="The default sleep time.",
        json_schema_extra={
            "env": "DEFAULT_SLEEP_TIME",
        },
    )

    TIME_FORMATTING: str = pydantic.Field(
        "%A - %d %B %Y %H:%M %Z",
        description="The default time formatting string.",
        json_schema_extra={
            "env": "TIME_FORMATTING",
        },
    )

    N_SLIDER_STEPS: int = pydantic.Field(
        36 * 60,
        description="The number of steps in the slider.",
        json_schema_extra={
            "env": "N_SLIDER_STEPS",
        },
    )


@functools.lru_cache
def get_settings() -> Settings:
    """Cached function to get the app settings.

    Returns:
        The app settings.
    """
    return Settings()


def initialize_logger(logging_level: int | None = None) -> None:
    """Initializes the logger.

    Args:
        logging_level: The logging level.
    """
    settings = get_settings()
    logger = logging.getLogger(settings.LOGGER_NAME)
    if logging_level:
        logger.setLevel(logging_level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
