from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PulseAccount(Base):
    """Transactional cache of a student's point totals.

    Always updated inside the same database transaction that appends the
    ledger entry. ``reconcile_account`` recomputes the values from the ledger
    so drift can be detected in tests.
    """

    __tablename__ = "pulse_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifetime_earned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    lifetime_redeemed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
