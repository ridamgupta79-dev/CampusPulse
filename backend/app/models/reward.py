from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Reward(Base):
    """A catalogue reward purchasable with Pulse Points.

    ``stock`` of ``None`` means unlimited availability. Simulated vouchers
    are demo fulfilments only and are labelled as such in ``description``.
    """

    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    sku: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # digital, simulated
    reward_type: Mapped[str] = mapped_column(String(20), nullable=False)

    cost: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    stock: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
