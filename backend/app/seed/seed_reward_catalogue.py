"""Idempotent reward-catalogue reference data.

Called on startup (outside production) alongside demo-user provisioning.
Purely additive: existing reward rows, prices, and stock are never modified
or deleted; only missing SKUs are inserted. Simulated vouchers are labelled
as demo rewards and never reference real partners or monetary value.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reward import Reward

REWARD_CATALOGUE: list[dict] = [
    {
        "sku": "CP-RWD-BADGE-25",
        "name": "Digital Achievement Badge",
        "description":
            "A collectible badge for your CampusPulse profile.",
        "reward_type": "digital",
        "cost": 25,
        "stock": None,
        "sort_order": 1,
    },
    {
        "sku": "CP-RWD-THEME-50",
        "name": "Avatar Frame / Profile Theme",
        "description":
            "Unlock a profile theme to customize your student portal.",
        "reward_type": "digital",
        "cost": 50,
        "stock": None,
        "sort_order": 2,
    },
    {
        "sku": "CP-RWD-CERT-75",
        "name": "Campus Appreciation Certificate",
        "description":
            "A digital certificate of appreciation from the demo campus.",
        "reward_type": "digital",
        "cost": 75,
        "stock": None,
        "sort_order": 3,
    },
    {
        "sku": "CP-RWD-PLANNER-100",
        "name": "Study Planner Template",
        "description":
            "A revision and study-planner template pack.",
        "reward_type": "digital",
        "cost": 100,
        "stock": None,
        "sort_order": 4,
    },
    {
        "sku": "CP-RWD-PREMIUM-150",
        "name": "Premium Profile Customization",
        "description":
            "Premium banner and accent customization for your profile.",
        "reward_type": "digital",
        "cost": 150,
        "stock": None,
        "sort_order": 5,
    },
    {
        "sku": "CP-RWD-PASS-200",
        "name": "Event Priority Pass (Simulated)",
        "description":
            "Demo reward: simulated priority entry to a campus workshop. "
            "Not a real event ticket.",
        "reward_type": "simulated",
        "cost": 200,
        "stock": None,
        "sort_order": 6,
    },
    {
        "sku": "CP-RWD-CAFE-300",
        "name": "Cafeteria Discount Voucher (Simulated)",
        "description":
            "Demo reward: simulated campus cafeteria discount. No real "
            "monetary value.",
        "reward_type": "simulated",
        "cost": 300,
        "stock": 5,
        "sort_order": 7,
    },
    {
        "sku": "CP-RWD-BOOK-500",
        "name": "Bookstore Voucher (Simulated)",
        "description":
            "Demo reward: simulated campus bookstore voucher. No real "
            "monetary value.",
        "reward_type": "simulated",
        "cost": 500,
        "stock": 2,
        "sort_order": 8,
    },
    {
        "sku": "CP-RWD-GIFT-750",
        "name": "Partner Gift-Card Voucher (Simulated)",
        "description":
            "Demo reward: simulated partner gift-card voucher used to show "
            "the top redemption tier. Not a real gift card; no partner "
            "relationship exists.",
        "reward_type": "simulated",
        "cost": 750,
        "stock": 1,
        "sort_order": 9,
    },
]


def seed_reward_catalogue(db: Session) -> int:
    """Insert missing catalogue rows; return the number added."""
    added = 0
    for item in REWARD_CATALOGUE:
        exists = db.scalar(
            select(Reward.id).where(Reward.sku == item["sku"])
        )
        if exists is not None:
            continue
        db.add(Reward(**item, is_synthetic=True, is_active=True))
        added += 1
    if added:
        db.commit()
    return added
