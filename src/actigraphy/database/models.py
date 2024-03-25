"""Database models for the actigraphy database."""

import datetime

import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.ext import hybrid

from actigraphy.database import database


class BaseTable(database.Base):  # type: ignore[misc]
    """Basic settings of a table. Contains an id, time_created, and time_updated."""

    __abstract__ = True

    id: orm.Mapped[int] = orm.mapped_column(primary_key=True, autoincrement=True)
    time_created: orm.Mapped[datetime.datetime] = orm.mapped_column(
        sqlalchemy.DateTime(timezone=True),
        server_default=sqlalchemy.func.now(),
    )
    time_updated: orm.Mapped[datetime.datetime] = orm.mapped_column(
        sqlalchemy.DateTime(timezone=True),
        server_default=sqlalchemy.func.now(),
        onupdate=sqlalchemy.func.now(),
    )


class BaseSleepTime(BaseTable):
    """Represents the basic sleep time record in the database."""

    __abstract__ = True

    onset: orm.Mapped[datetime.datetime] = orm.mapped_column(
        sqlalchemy.DateTime,
        nullable=False,
    )
    onset_utc_offset: orm.Mapped[int] = orm.mapped_column(
        sqlalchemy.Integer,
        nullable=False,
    )
    wakeup: orm.Mapped[datetime.datetime] = orm.mapped_column(
        sqlalchemy.DateTime,
        nullable=False,
    )
    wakeup_utc_offset: orm.Mapped[int] = orm.mapped_column(
        sqlalchemy.Integer,
        nullable=False,
    )

    @hybrid.hybrid_property
    def onset_with_tz(self) -> datetime.datetime:
        """Returns the onset time of the event with the timezone information added.

        Returns:
            datetime.datetime: The onset time with timezone information.
        """
        onset_utc = self.onset.replace(tzinfo=datetime.UTC)
        return onset_utc.astimezone(
            datetime.timezone(datetime.timedelta(seconds=self.onset_utc_offset)),
        )

    @hybrid.hybrid_property
    def wakeup_with_tz(self) -> datetime.datetime:
        """Returns the wakeup time of the event with the timezone information added.

        Returns:
            datetime.datetime: The wakeup time with timezone information.
        """
        wakeup_utc = self.wakeup.replace(tzinfo=datetime.UTC)
        return wakeup_utc.astimezone(
            datetime.timezone(datetime.timedelta(seconds=self.wakeup_utc_offset)),
        )

    @hybrid.hybrid_property
    def duration(self) -> datetime.timedelta:
        """Returns the duration of the sleep period.

        Returns:
            datetime.timedelta: The duration of the sleep period.
        """
        return self.wakeup - self.onset


class SleepTime(BaseSleepTime):
    """Represents a sleep time record in the database.

    Attributes:
        id: The unique identifier of the sleep time record.
        onset: The date and time when the sleep started.
        onset_utc_offset: The UTC offset of the onset in seconds.
        wakeup: The date and time when the sleep ended.
        wakeup_utc_offset: The UTC offset of the wakeup in seconds.
        day: The day when the sleep occurred.
    """

    __tablename__ = "sleep_times"

    day_id: orm.Mapped[int] = orm.mapped_column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("days.id"),
        nullable=False,
    )

    day = orm.relationship("Day", back_populates="sleep_times")


class GGIRSleepTime(BaseSleepTime):
    """Represents the original GGIR sleep times."""

    __tablename__ = "ggir_sleep_times"

    day_id: orm.Mapped[int] = orm.mapped_column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("days.id"),
        nullable=False,
    )

    day = orm.relationship("Day", back_populates="ggir_sleep_times")


class DataPoint(BaseTable):
    """Represents a data point in the database.

    Attributes:
        id: The unique identifier of the data point.
        time: The date and time of the data point.
        time_utc_offset: The UTC offset of the time in seconds.
        value: The value of the data point.
        day: The day to which the data point belongs.
    """

    __tablename__ = "data_points"

    timestamp: orm.Mapped[datetime.datetime] = orm.mapped_column(
        sqlalchemy.DateTime,
        nullable=False,
    )
    timestamp_utc_offset: orm.Mapped[int] = orm.mapped_column(
        sqlalchemy.Integer,
        nullable=False,
    )
    sensor_angle: orm.Mapped[float] = orm.mapped_column(
        sqlalchemy.Float,
        nullable=False,
    )
    sensor_acceleration: orm.Mapped[float] = orm.mapped_column(
        sqlalchemy.Float,
        nullable=False,
    )
    non_wear: orm.Mapped[bool] = orm.mapped_column(
        sqlalchemy.Boolean,
        nullable=False,
    )
    subject_id = orm.mapped_column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("subjects.id"),
        nullable=False,
    )

    subject = orm.relationship("Subject", back_populates="data_points")

    @hybrid.hybrid_property
    def timestamp_with_tz(self) -> datetime.datetime:
        """Returns the time of the event with the timezone information added.

        Returns:
            datetime.datetime: The time with timezone information.
        """
        time_utc = self.timestamp.replace(tzinfo=datetime.UTC)
        return time_utc.astimezone(
            datetime.timezone(datetime.timedelta(seconds=self.timestamp_utc_offset)),
        )


class Day(BaseTable):
    """A class representing a day in the database.

    Combinations of subjects and dates must be unique.

    Attributes:
        date: The date of the day.
        is_missing_sleep: Whether the day is missing sleep data.
        is_multiple_sleep: Whether the day has multiple sleep periods.
        is_reviewed: Whether the day has been reviewed.
        subject: The subject to which the day belongs.
        sleep_times: The sleep times associated with the day.
    """

    __tablename__ = "days"
    __table_args__ = (
        sqlalchemy.UniqueConstraint("subject_id", "date", name="uq_subject_date"),
    )

    date: orm.Mapped[datetime.date] = orm.mapped_column(
        sqlalchemy.Date,
        nullable=False,
    )
    is_missing_sleep: orm.Mapped[bool] = orm.mapped_column(
        sqlalchemy.Boolean,
        default=False,
    )
    is_multiple_sleep: orm.Mapped[bool] = orm.mapped_column(
        sqlalchemy.Boolean,
        default=False,
    )
    is_reviewed: orm.Mapped[bool] = orm.mapped_column(
        sqlalchemy.Boolean,
        default=False,
    )
    subject_id: orm.Mapped[int] = orm.mapped_column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("subjects.id"),
        nullable=False,
    )

    subject = orm.relationship(
        "Subject",
        back_populates="days",
    )
    sleep_times = orm.relationship(
        "SleepTime",
        back_populates="day",
        cascade="all, delete",
    )
    ggir_sleep_times = orm.relationship(
        "GGIRSleepTime",
        back_populates="day",
        cascade="all, delete",
    )


class Subject(BaseTable):
    """A class representing a subject in the actigraphy database.

    Attributes:
        is_finished: Whether the subject has finished the study or not.
        days: A list of Day objects associated with the subject.
    """

    __tablename__ = "subjects"

    name: orm.Mapped[str] = orm.mapped_column(
        sqlalchemy.String(128),
        nullable=False,
        unique=True,
    )
    n_points_per_day: orm.Mapped[int] = orm.mapped_column(
        sqlalchemy.Integer,
        nullable=False,
    )
    is_finished: orm.Mapped[bool] = orm.mapped_column(
        sqlalchemy.Boolean,
        default=False,
    )

    days = orm.relationship(
        "Day",
        back_populates="subject",
        cascade="all, delete",
    )
    data_points = orm.relationship(
        "DataPoint",
        back_populates="subject",
        cascade="all, delete",
    )
