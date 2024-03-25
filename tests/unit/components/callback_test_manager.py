"""Initialize the callback manager for unit tests."""

from collections.abc import Callable
from typing import Any

from actigraphy.core import callback_manager

manager = callback_manager.global_manager
callback_manager.initialize_components()


def get_callback(name: str) -> Callable[..., Any]:
    """Returns the callback with the given name.

    Args:
        name: The name of the callback.

    Returns:
        Callable[[Any], Any]: The callback with the given name.
    """
    for callback in manager._callbacks:  # pylint: disable=protected-access
        if callback.func.__name__ == name:
            return callback.func
    msg = f"Callback {name} not found."
    raise ValueError(msg)
