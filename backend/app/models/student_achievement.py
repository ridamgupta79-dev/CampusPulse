from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StudentAchievement(Base):
    """A non-punitive milestone derived from real student records.

    ``code`` is one of: first_submission, five_submissions,
    early_submission, first_redemption. The unique pair constraint
    prevents duplicate awards.
    """

    __tablename__ = "student_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "code",
            name="uq_achievement_student_code",
        ),
    )
