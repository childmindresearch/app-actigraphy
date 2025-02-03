"""Tests the switches callbacks.

Due to the custom nature of the callbacks, it is not possible to call them
directly. Instead, we use global manager to get the callback function and then
call it with the appropriate arguments.
"""

from typing import NamedTuple

from pytest_mock import plugin

from . import callback_test_manager


def test_update_switches(
    mocker: plugin.MockerFixture,
    file_manager: dict[str, str],
) -> None:
    """Test the update_switches function."""

    class MockReturn(NamedTuple):
        is_multiple_sleep: bool = True
        is_missing_sleep: bool = True
        is_reviewed: bool = True

    expected_status_flags = (True, True, True)
    mocker.patch(
        "actigraphy.components.switches.crud.read_day_by_subject",
        return_value=MockReturn(),
    )
    update_switches_callback = callback_test_manager.get_callback("update_switches")

    actual_status_flags = update_switches_callback(0, file_manager)

    assert actual_status_flags == expected_status_flags, (
        "update_switches did not return the expected status flags"
    )
