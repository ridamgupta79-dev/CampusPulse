from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StudentNotification(Base):
    """Persistent, per-student notification with read/unread state."""

    __tablename__ = "student_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # assignment_published, deadline_approaching, submission_received,
    # submission_late, feedback_released, points_awarded,
    # redemption_completed, adjustment, achievement_unlocked
    category: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    assignment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submission_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

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
