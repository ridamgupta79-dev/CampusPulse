
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def signal_utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


class StudentSignal(Base):
    """A timestamped observation from a student-success data domain."""

    __tablename__ = "student_signals"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    domain: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )

    signal_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    numeric_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    text_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=signal_utc_now,
        nullable=False,
        index=True,
    )

    source_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    quality_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="valid",
    )

    purpose_category: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
