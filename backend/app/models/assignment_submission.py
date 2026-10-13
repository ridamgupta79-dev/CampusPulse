from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AssignmentSubmission(Base):
    """A student's submission for one assignment (one row per pair).

    Resubmission before grading replaces the answer and refreshes the
    server-recorded timestamp; grading finalizes the row and locks further
    edits. The unique pair constraint guarantees at most one submission row,
    which the ledger idempotency key builds on.
    """

    __tablename__ = "assignment_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    text_answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # submitted, graded, returned
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="submitted",
        index=True,
    )

    is_late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )

    resubmission_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    marks_obtained: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Quality rubric 0-3 assigned by an authorized teacher.
    quality_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    feedback_released: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    graded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    graded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    timing_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "student_id",
            name="uq_submission_assignment_student",
        ),
    )

    student: Mapped["Student"] = relationship("Student", lazy="joined")
