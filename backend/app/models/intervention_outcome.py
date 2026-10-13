
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def outcome_utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


class InterventionOutcome(Base):
    """Stores an intervention's measured or documented outcome."""

    __tablename__ = "intervention_outcomes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    intervention_id: Mapped[int] = mapped_column(
        ForeignKey("interventions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    metric_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    baseline_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    baseline_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    follow_up_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    follow_up_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    classification: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="insufficient_evidence",
    )

    outcome_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    evidence_quality: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="unknown",
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=outcome_utc_now,
        nullable=False,
        index=True,
    )
