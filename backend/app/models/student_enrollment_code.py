from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StudentEnrollmentCode(Base):
    """Single-use code that safely binds a student account to a record.

    Knowing a student code is not enough to claim a record; the claiming
    account must also present a random enrollment code issued for that exact
    record by an authorized staff member (or the local demo seeder).
    """

    __tablename__ = "student_enrollment_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    issued_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    redeemed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    redeemed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("student_id", "redeemed_by_user_id",
                         name="uq_enrollment_student_redeemer"),
    )
