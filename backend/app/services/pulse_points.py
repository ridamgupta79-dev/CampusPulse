"""Pulse Points engine: server-side scoring, ledger, and balances.

Rules implemented here (also documented in docs/student-portal.md):

Timing rubric (0-4 points), computed only from server-recorded timestamps:

- Let ``window = due_at - published_at`` and ``remaining = due_at - submitted_at``.
- On time (``remaining > 0``):
    - ``remaining >= 20%`` of window ................ 4 points
    - ``10% <= remaining < 20%`` of window ......... 3 points
    - ``0 < remaining < 10%`` of window ............ 2 points
    - Degenerate ``window <= 0`` ................... 4 points
- At/after the deadline, when late submissions are allowed:
    - late by at most ``late_window_hours`` ........ 1 point
    - later than the late window ................... 0 points
- Submitted outside the permitted window .......... no award (rejected upstream).

Quality rubric (0-3 points) is assigned by an authorized teacher during
review. The final award is ``timing + quality`` capped at 7 per submission.
Historical awards are immutable; corrections use adjustment/reversal entries.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.pulse_account import PulseAccount
from app.models.pulse_ledger import PulseLedgerEntry
from app.models.reward import Reward
from app.models.reward_redemption import RewardRedemption
from app.models.student_notification import StudentNotification

EARN_TXN_TYPES = ("award", "refund", "adjustment", "reversal")


def compute_timing_points(
    published_at: datetime,
    due_at: datetime,
    submitted_at: datetime,
    allow_late: bool,
    late_window_hours: int,
) -> int:
    """Compute the documented timing score from server-side timestamps."""
    if submitted_at.tzinfo is None:
        submitted_at = submitted_at.replace(tzinfo=timezone.utc)
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    window = (due_at - published_at).total_seconds()
    remaining = (due_at - submitted_at).total_seconds()

    if remaining > 0:
        if window <= 0:
            return 4
        fraction = remaining / window
        if fraction >= 0.20:
            return 4
        if fraction >= 0.10:
            return 3
        return 2

    late_by_hours = (-remaining) / 3600.0
    if allow_late and late_by_hours <= late_window_hours:
        return 1
    return 0


def ensure_account(db: Session, student_id: int) -> PulseAccount:
    """Return the student's point account, creating it on first use."""
    account = db.scalar(
        select(PulseAccount).where(PulseAccount.student_id == student_id)
    )
    if account is None:
        account = PulseAccount(student_id=student_id)
        db.add(account)
        db.flush()
    return account


def get_balance(db: Session, student_id: int) -> int:
    """Authoritative spendable balance (ledger-derived, cached on account)."""
    account = db.scalar(
        select(PulseAccount).where(PulseAccount.student_id == student_id)
    )
    if account is None:
        return 0
    return int(account.balance)


def net_earned(db: Session, student_id: int) -> int:
    """Lifetime net earned points used for leaderboard ranking.

    Redemptions (spending) do not reduce net earned; adjustments, reversals,
    and refunds do, because they correct the earning record itself.
    """
    total = db.scalar(
        select(func.coalesce(func.sum(PulseLedgerEntry.amount), 0)).where(
            PulseLedgerEntry.student_id == student_id,
            PulseLedgerEntry.txn_type != "redemption",
        )
    )
    return int(total or 0)


def _append_ledger_and_update_account(
    db: Session,
    *,
    student_id: int,
    txn_type: str,
    amount: int,
    idempotency_key: str,
    reason: str = "",
    assignment_id: int | None = None,
    submission_id: int | None = None,
    reward_id: int | None = None,
    redemption_id: int | None = None,
    timing_points: int | None = None,
    quality_points: int | None = None,
    actor_user_id: int | None = None,
) -> PulseLedgerEntry | None:
    """Append one ledger entry and apply it to the cached account atomically.

    Returns the created entry, or ``None`` when the idempotency key already
    exists (a retry) so callers can no-op without duplicating history.
    """
    existing = db.scalar(
        select(PulseLedgerEntry).where(
            PulseLedgerEntry.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        return None

    entry = PulseLedgerEntry(
        student_id=student_id,
        txn_type=txn_type,
        amount=amount,
        idempotency_key=idempotency_key,
        reason=reason,
        assignment_id=assignment_id,
        submission_id=submission_id,
        reward_id=reward_id,
        redemption_id=redemption_id,
        timing_points=timing_points,
        quality_points=quality_points,
        actor_user_id=actor_user_id,
    )
    db.add(entry)

    account = ensure_account(db, student_id)
    account.balance = int(account.balance) + amount
    if txn_type == "redemption":
        account.lifetime_redeemed = int(account.lifetime_redeemed) + abs(amount)
    else:
        # Awards and corrections (refund/adjustment/reversal) all adjust the
        # lifetime net earned figure, matching the leaderboard metric.
        account.lifetime_earned = int(account.lifetime_earned) + amount

    db.flush()
    return entry


def award_for_submission(
    db: Session,
    *,
    submission_id: int,
    student_id: int,
    assignment_id: int,
    timing_points: int,
    quality_points: int,
    actor_user_id: int | None,
) -> PulseLedgerEntry | None:
    """Create the single final award for a graded submission.

    Called inside the grade-release transaction. Idempotent per submission:
    retries return ``None`` and never create a second award.
    """
    timing = max(0, min(4, int(timing_points)))
    quality = max(0, min(3, int(quality_points)))
    total = min(7, timing + quality)

    return _append_ledger_and_update_account(
        db,
        student_id=student_id,
        txn_type="award",
        amount=total,
        idempotency_key=f"award:submission:{submission_id}",
        reason="Assignment award (timing + quality rubric)",
        assignment_id=assignment_id,
        submission_id=submission_id,
        timing_points=timing,
        quality_points=quality,
        actor_user_id=actor_user_id,
    )


def adjust_points(
    db: Session,
    *,
    student_id: int,
    amount: int,
    txn_type: str,
    reason: str,
    actor_user_id: int | None,
    idempotency_key: str,
    assignment_id: int | None = None,
    submission_id: int | None = None,
    redemption_id: int | None = None,
    reward_id: int | None = None,
) -> PulseLedgerEntry | None:
    """Record an explicit refund, adjustment, or reversal entry."""
    if txn_type not in ("refund", "adjustment", "reversal"):
        raise ValueError(f"Unsupported adjustment txn_type: {txn_type}")
    if amount == 0:
        raise ValueError("Adjustment amount must be non-zero.")

    return _append_ledger_and_update_account(
        db,
        student_id=student_id,
        txn_type=txn_type,
        amount=amount,
        idempotency_key=idempotency_key,
        reason=reason,
        assignment_id=assignment_id,
        submission_id=submission_id,
        redemption_id=redemption_id,
        reward_id=reward_id,
        actor_user_id=actor_user_id,
    )


def redeem_reward(
    db: Session,
    *,
    student_id: int,
    reward: Reward,
) -> tuple[RewardRedemption | None, str]:
    """Redeem a reward atomically.

    The balance re-check, stock decrement, redemption record, ledger entry,
    and account update all happen in the caller's single transaction, so
    concurrent redemptions cannot overspend the same balance.
    """
    account = ensure_account(db, student_id)
    balance = int(account.balance)

    if balance < reward.cost:
        return None, "Insufficient Pulse Points for this reward."

    if not reward.is_active:
        return None, "This reward is not currently available."

    if reward.stock is not None and reward.stock <= 0:
        return None, "This reward is out of stock."

    previous_redemption = db.scalar(
        select(RewardRedemption).where(
            RewardRedemption.student_id == student_id,
            RewardRedemption.reward_id == reward.id,
            RewardRedemption.status == "completed",
        )
    )
    if previous_redemption is not None:
        return None, "You have already redeemed this reward."

    if reward.stock is not None:
        updated = (
            db.query(Reward)
            .filter(Reward.id == reward.id, Reward.stock > 0)
            .update({"stock": Reward.stock - 1}, synchronize_session=False)
        )
        if updated == 0:
            return None, "This reward is out of stock."

    redemption = RewardRedemption(
        reference="pending",
        student_id=student_id,
        reward_id=reward.id,
        cost_at_redemption=reward.cost,
        status="completed",
    )
    db.add(redemption)
    db.flush()

    redemption.reference = f"CP-RED-{redemption.id:08d}"

    entry = _append_ledger_and_update_account(
        db,
        student_id=student_id,
        txn_type="redemption",
        amount=-reward.cost,
        idempotency_key=f"redeem:{student_id}:{reward.id}",
        reason=f"Redeemed: {reward.name}",
        reward_id=reward.id,
        redemption_id=redemption.id,
    )
    if entry is None:
        # A concurrent identical redemption already committed.
        db.rollback()
        return None, "You have already redeemed this reward."

    db.flush()
    return redemption, "Redemption complete."


def reconcile_account(db: Session, student_id: int) -> dict:
    """Recompute cached account totals from the immutable ledger."""
    total = int(
        db.scalar(
            select(func.coalesce(func.sum(PulseLedgerEntry.amount), 0)).where(
                PulseLedgerEntry.student_id == student_id,
            )
        )
        or 0
    )
    redeemed_total = int(
        db.scalar(
            select(func.coalesce(func.sum(PulseLedgerEntry.amount), 0)).where(
                PulseLedgerEntry.student_id == student_id,
                PulseLedgerEntry.txn_type == "redemption",
            )
        )
        or 0
    )

    account = ensure_account(db, student_id)
    account.balance = total
    account.lifetime_earned = total - redeemed_total
    account.lifetime_redeemed = abs(redeemed_total)
    db.flush()

    return {
        "balance": account.balance,
        "lifetime_earned": account.lifetime_earned,
        "lifetime_redeemed": account.lifetime_redeemed,
    }


def create_notification(
    db: Session,
    *,
    student_id: int,
    category: str,
    title: str,
    body: str,
    assignment_id: int | None = None,
    submission_id: int | None = None,
    is_synthetic: bool = False,
) -> StudentNotification:
    """Persist one notification for the student."""
    notification = StudentNotification(
        student_id=student_id,
        category=category,
        title=title,
        body=body,
        assignment_id=assignment_id,
        submission_id=submission_id,
        is_synthetic=is_synthetic,
    )
    db.add(notification)
    db.flush()
    return notification
