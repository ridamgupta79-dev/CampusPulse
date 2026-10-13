
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


class Student(Base):
    """Core academic profile for a synthetic CampusPulse student."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    student_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    program: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    department: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    year_of_study: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    cohort: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    advisor_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    mentor_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
