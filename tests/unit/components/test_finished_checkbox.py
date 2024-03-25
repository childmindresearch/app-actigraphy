"""Unit tests for the finished_checkbox module."""

from sqlalchemy import orm

from actigraphy.database import models

from . import callback_test_manager


def _get_subject(session: orm.Session, identifier: str) -> models.Subject:
    """Returns the subject with the given identifier.

    Args:
        session: The database session.
        identifier: The identifier of the subject.

    Returns:
        models.Subject: The subject model.
    """
    subject = (
        session.query(models.Subject)
        .filter(
            models.Subject.name == identifier,
        )
        .first()
    )

    if subject:
        return subject
    msg = f"Subject {identifier} not found in database"
    raise ValueError(msg)


def test_write_log_done(session: orm.Session, file_manager: dict[str, str]) -> None:
    """Test the write_log_done function."""
    subject_before = _get_subject(session, file_manager["identifier"])
    func = callback_test_manager.get_callback("write_log_done")

    actual = func("is done", file_manager)
    subject_after = _get_subject(session, file_manager["identifier"])

    assert actual is True
    assert subject_before.is_finished is False
    assert subject_after.is_finished is True
