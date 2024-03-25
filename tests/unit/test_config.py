"""Unit tests for the config module."""

import logging

from pytest_mock import plugin

from actigraphy.core import config


def test_initialize_logger_default_level(mocker: plugin.MockerFixture) -> None:
    """Test that the logger is initialized with the default level."""
    mock_get_settings = mocker.patch(
        "actigraphy.core.config.get_settings",
        autospec=True,
    )
    mock_settings = mock_get_settings.return_value
    mock_settings.LOGGER_NAME = "test_logger"

    mock_get_logger = mocker.patch("logging.getLogger", autospec=True)
    mock_logger = mock_get_logger.return_value

    config.initialize_logger()

    mock_get_logger.assert_called_once_with("test_logger")
    mock_logger.setLevel.assert_not_called()
    assert isinstance(mock_logger.addHandler.call_args[0][0], logging.StreamHandler)


def test_initialize_logger_custom_level(mocker: plugin.MockerFixture) -> None:
    """Test that the logger is initialized with a custom level."""
    mock_get_settings = mocker.patch(
        "actigraphy.core.config.get_settings",
        autospec=True,
    )
    mock_settings = mock_get_settings.return_value
    mock_settings.LOGGER_NAME = "test_logger"
    mock_get_logger = mocker.patch("logging.getLogger", autospec=True)
    mock_logger = mock_get_logger.return_value
    custom_level = logging.DEBUG

    config.initialize_logger(custom_level)

    mock_get_logger.assert_called_once_with("test_logger")
    mock_logger.setLevel.assert_called_once_with(custom_level)
    assert isinstance(mock_logger.addHandler.call_args[0][0], logging.StreamHandler)


def test_initialize_logger_handler_formatting(mocker: plugin.MockerFixture) -> None:
    """Test that the logger's handler is set with the correct formatting."""
    mock_get_settings = mocker.patch(
        "actigraphy.core.config.get_settings",
        autospec=True,
    )
    mock_settings = mock_get_settings.return_value
    mock_settings.LOGGER_NAME = "test_logger"
    mock_get_logger = mocker.patch("logging.getLogger", autospec=True)
    mock_logger = mock_get_logger.return_value

    config.initialize_logger()
    added_handler = mock_logger.addHandler.call_args[0][0]

    assert isinstance(added_handler, logging.StreamHandler)
    assert isinstance(added_handler.formatter, logging.Formatter)
    assert (
        added_handler.formatter._fmt
        == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # pylint: disable=protected-access
    )
