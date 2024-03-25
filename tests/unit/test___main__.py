"""Unit tests for the __main__ module."""

from pytest_mock import plugin

from actigraphy import __main__


def test___main__(mocker: plugin.MockerFixture) -> None:
    """Tests that the __main__ function calls create_app and runs the server."""
    mock_dash_app = mocker.MagicMock()
    mock_create_app = mocker.patch(
        "actigraphy.__main__.app.create_app",
        return_value=mock_dash_app,
    )

    __main__.main_entrypoint()

    mock_create_app.assert_called_once()
    mock_dash_app.run_server.assert_called_once_with(port=8051, host="0.0.0.0")  # noqa: S104
