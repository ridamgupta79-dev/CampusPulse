
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def event_utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


class InterventionEvent(Base):
    """A timestamped record of an intervention action or follow-up."""

    __tablename__ = "intervention_events"

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

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    actor_role: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    actor_label: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=event_utc_now,
        nullable=False,
        index=True,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    event_metadata: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
    )
