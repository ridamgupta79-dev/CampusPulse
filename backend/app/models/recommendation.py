
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def recommendation_utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


class Recommendation(Base):
    """A proposed student-support action awaiting human review."""

    __tablename__ = "recommendations"

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

    assessment_id: Mapped[int | None] = mapped_column(
        ForeignKey("risk_assessments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    intervention_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    rationale: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    contributing_signals: Mapped[list | dict] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    intended_role: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    suggested_next_step: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="proposed",
        index=True,
    )

    decision_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=recommendation_utc_now,
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=recommendation_utc_now,
        onupdate=recommendation_utc_now,
        nullable=False,
    )
