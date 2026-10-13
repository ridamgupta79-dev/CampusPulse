from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_redemption_reference(redemption_id: int) -> str:
    """Stable, human-readable redemption reference."""
    return f"CP-RED-{redemption_id:08d}"


class RewardRedemption(Base):
    """A completed (or refunded) purchase of a reward with Pulse Points."""

    __tablename__ = "reward_redemptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    reference: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reward_id: Mapped[int] = mapped_column(
        ForeignKey("rewards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    cost_at_redemption: Mapped[int] = mapped_column(Integer, nullable=False)

    # completed, refunded
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="completed",
        index=True,
    )

    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "reward_id",
            "status",
            name="uq_redemption_student_reward_active",
        ),
    )
