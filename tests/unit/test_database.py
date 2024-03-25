"""Tests for the database module."""

import sqlalchemy

from actigraphy.database import database


def test_database_initialization(in_memory_db: database.Database) -> None:
    """Test database initialization with an in-memory SQLite database."""
    assert in_memory_db.engine.url.database == ":memory:"


def test_database_schema_creation(in_memory_db: database.Database) -> None:
    """Test that the database schema is created successfully."""
    in_memory_db.create_database()
    inspector = sqlalchemy.inspect(in_memory_db.engine)
    assert "subjects" in inspector.get_table_names()


def test_session_generator_activate() -> None:
    """Test the session generator function."""
    session = next(database.session_generator(":memory:"))

    assert session.is_active
