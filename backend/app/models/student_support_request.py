from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StudentSupportRequest(Base):
    """A student-initiated, human-reviewed support request.

    Requests never trigger automatic punitive action or diagnosis. Internal
    staff notes stay staff-only; only ``student_visible_response`` is returned
    to the student.
    """

    __tablename__ = "student_support_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # academic_checkin, mentor_support, assignment_clarification
    request_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )

    subject: Mapped[str] = mapped_column(String(150), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # open, in_review, resolved
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        index=True,
    )

    assigned_role: Mapped[str | None] = mapped_column(String(30), nullable=True)

    staff_internal_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    student_visible_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
