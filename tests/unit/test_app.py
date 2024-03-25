"""Unit tests for the app module."""

from unittest import mock

import dash_bootstrap_components
from pytest_mock import plugin

from actigraphy import app


def test_create_app(mocker: plugin.MockerFixture) -> None:
    """Test the create_app function.

    As this function calls other functions, we only check that the correct
    functions are called with the correct arguments. The functions themselves
    are tested in their own unit tests.
    """
    mocker.patch(
        "actigraphy.app.cli.parse_args",
        return_value=mocker.MagicMock(verbosity=20),
    )
    mock_initialize_logger = mocker.patch("actigraphy.app.config.initialize_logger")
    mock_logger = mocker.patch("logging.getLogger")
    mock_dash = mocker.patch("actigraphy.app.dash.Dash", autospec=True)
    mocker.patch("actigraphy.app.callback_manager.initialize_components")
    mocker.patch("actigraphy.app.callback_manager.global_manager.attach_to_app")
    mocker.patch(
        "actigraphy.app.cli.get_subject_folders",
        return_value=["dir1", "dir2"],
    )
    mocker.patch(
        "actigraphy.app.file_selection.file_selection",
        return_value=mocker.MagicMock(),
    )
    mocker.patch(
        "actigraphy.app.app_license.app_license",
        return_value=mocker.MagicMock(),
    )

    actual = app.create_app()

    mock_initialize_logger.assert_called_once_with(logging_level=20)
    mock_logger.assert_called_once_with(app.LOGGER_NAME)
    assert isinstance(actual, mock.NonCallableMagicMock)
    mock_dash.assert_called_once_with(
        app.APP_NAME,
        external_stylesheets=[dash_bootstrap_components.themes.BOOTSTRAP],
    )
    assert actual.title == app.APP_NAME
