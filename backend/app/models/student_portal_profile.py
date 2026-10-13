from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StudentPortalProfile(Base):
    """Student-editable contact and summary fields.

    Kept in a separate table so the institutional ``students`` table (official
    marks, identifiers, cohort data) is never student-editable. Institutional
    identifiers and marks stay read-only for students.
    """

    __tablename__ = "student_portal_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    contact_email: Mapped[str | None] = mapped_column(
        String(254),
        nullable=True,
    )

    contact_phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    skills: Mapped[str | None] = mapped_column(Text, nullable=True)

    certifications: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
