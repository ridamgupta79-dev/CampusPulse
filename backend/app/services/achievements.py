"""Non-punitive achievement milestones derived from real records.

Every grant is guarded by the unique (student_id, code) constraint, so
repeated evaluation can never duplicate an achievement. Unlocking an
achievement also creates a persistent notification.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assignment_submission import AssignmentSubmission
from app.models.reward_redemption import RewardRedemption
from app.models.student_achievement import StudentAchievement
from app.services.pulse_points import create_notification

ACHIEVEMENT_META: dict[str, dict[str, str]] = {
    "first_submission": {
        "title": "First Assignment Submitted",
        "description": "You completed your first assignment submission.",
    },
    "five_submissions": {
        "title": "Five Assignments Completed",
        "description": "You have submitted five assignments. Keep going!",
    },
    "early_submission": {
        "title": "Early Submission Achievement",
        "description": "You earned the full timing score by submitting early.",
    },
    "first_redemption": {
        "title": "First Reward Redeemed",
        "description": "You redeemed your first reward from the marketplace.",
    },
}


def _grant(db: Session, student_id: int, code: str, is_synthetic: bool = False) -> bool:
    """Grant one achievement if not already present. Returns True if new."""
    existing = db.scalar(
        select(StudentAchievement).where(
            StudentAchievement.student_id == student_id,
            StudentAchievement.code == code,
        )
    )
    if existing is not None:
        return False

    db.add(StudentAchievement(
        student_id=student_id,
        code=code,
        is_synthetic=is_synthetic,
    ))
    db.flush()

    meta = ACHIEVEMENT_META.get(code, {})
    create_notification(
        db,
        student_id=student_id,
        category="achievement_unlocked",
        title=f"Achievement unlocked: {meta.get('title', code)}",
        body=meta.get("description", ""),
        is_synthetic=is_synthetic,
    )
    return True


def evaluate_submission_achievements(
    db: Session,
    *,
    student_id: int,
    timing_points: int | None = None,
    is_synthetic: bool = False,
) -> list[str]:
    """Re-derive submission milestones after a submission or grading event."""
    unlocked: list[str] = []

    submitted_count = int(
        db.scalar(
            select(func.count(AssignmentSubmission.id)).where(
                AssignmentSubmission.student_id == student_id,
            )
        )
        or 0
    )

    if submitted_count >= 1 and _grant(db, student_id, "first_submission", is_synthetic):
        unlocked.append("first_submission")
    if submitted_count >= 5 and _grant(db, student_id, "five_submissions", is_synthetic):
        unlocked.append("five_submissions")
    if timing_points is not None and timing_points >= 4:
        if _grant(db, student_id, "early_submission", is_synthetic):
            unlocked.append("early_submission")

    return unlocked


def evaluate_redemption_achievements(
    db: Session,
    *,
    student_id: int,
    is_synthetic: bool = False,
) -> list[str]:
    """Grant the first-redemption milestone when a redemption exists."""
    redeemed_count = int(
        db.scalar(
            select(func.count(RewardRedemption.id)).where(
                RewardRedemption.student_id == student_id,
                RewardRedemption.status == "completed",
            )
        )
        or 0
    )

    if redeemed_count >= 1 and _grant(db, student_id, "first_redemption", is_synthetic):
        return ["first_redemption"]
    return []
