from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PulseLedgerEntry(Base):
    """Immutable signed point transaction; the source of truth for balances.

    Historical awards are never rewritten. Corrections are recorded as
    separate adjustment or reversal entries. ``idempotency_key`` is unique so
    retries, double clicks, or concurrent requests cannot award twice.
    """

    __tablename__ = "pulse_ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # award, redemption, refund, adjustment, reversal
    txn_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey("assignments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    submission_id: Mapped[int | None] = mapped_column(
        ForeignKey("assignment_submissions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    reward_id: Mapped[int | None] = mapped_column(
        ForeignKey("rewards.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    redemption_id: Mapped[int | None] = mapped_column(
        ForeignKey("reward_redemptions.id", ondelete="SET NULL"),
        nullable=True,
    )

    reason: Mapped[str] = mapped_column(String(300), nullable=False, default="")

    timing_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )
