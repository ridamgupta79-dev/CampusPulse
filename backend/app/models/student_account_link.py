from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StudentAccountLink(Base):
    """One-to-one binding between a student account and a student record.

    A user account with the ``student`` role gains access to exactly one
    student record through this table. Both columns are unique so an account
    cannot claim multiple records and a record cannot be shared by accounts.
    """

    __tablename__ = "student_account_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
