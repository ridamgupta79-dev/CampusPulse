from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Assignment(Base):
    """A teacher-authored assignment targeted at one student cohort."""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    instructions: Mapped[str] = mapped_column(Text, nullable=False, default="")

    subject: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    cohort: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    teacher_user_id: Mapped[int] = mapped_column(
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # draft, published, closed
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        index=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    max_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # Prototype supports text and optional reference-link submissions;
    # no file storage exists, so file uploads are never accepted.
    accepted_submission_types: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        default="text,link",
    )

    allow_late_submissions: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    late_window_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=24,
    )

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
