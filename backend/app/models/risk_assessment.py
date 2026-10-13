
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def assessment_utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


class RiskAssessment(Base):
    """Stores an explainable student-success review assessment."""

    __tablename__ = "risk_assessments"

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

    score: Mapped[float | None] = mapped_column(nullable=True)

    risk_band: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="needs_review",
        index=True,
    )

    factor_breakdown: Mapped[list | dict] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    data_quality_notes: Mapped[list | dict] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    rule_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=assessment_utc_now,
        nullable=False,
        index=True,
    )
