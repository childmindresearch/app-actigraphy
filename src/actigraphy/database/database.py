"""A module for interacting with the SQL database."""

import logging
import pathlib
from collections import abc

import sqlalchemy
from sqlalchemy import orm, pool

from actigraphy.core import config

settings = config.get_settings()
LOGGER_NAME = settings.LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)

Base = orm.declarative_base()


class Database:
    """A class representing a database connection."""

    def __init__(self, path: str | pathlib.Path) -> None:
        """Initializes a new instance of the Database class.

        The Database class provides a high-level interface for interacting with a
        PostgreSQL database.

        Args:
            path: The path to the database file.
        """
        logger.debug("Initializing database engine.")

        self.engine = sqlalchemy.create_engine(
            url=f"sqlite:///{path}",
            poolclass=pool.StaticPool,
            connect_args={"check_same_thread": False},
        )
        self.session_factory = orm.scoped_session(
            orm.sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
            ),
        )

    def create_database(self) -> None:
        """Creates the database schema."""
        logger.debug("Creating database schema.")
        Base.metadata.create_all(self.engine)


def session_generator(
    path: str | pathlib.Path,
) -> abc.Generator[orm.Session, None, None]:
    """Returns a generator for a session instance.

    Returns:
        orm.Session: A database session.

    Notes:
        A generator is used to ensure that the session is closed after use.
    """
    session = Database(path).session_factory()
    try:
        yield session
    finally:
        session.close()
