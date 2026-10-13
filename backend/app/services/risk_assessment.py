
"""Explainable, consent-aware academic support assessment rules."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RiskAssessment, Student, StudentConsent, StudentSignal

RULE_VERSION = "academic-support-v1"
STALE_AFTER_DAYS = 30

THRESHOLDS = {
    "attendance_percentage": {
        "threshold": 75.0,
        "direction": "below",
        "weight": 35,
        "domain": "attendance",
        "rationale": "Attendance below 75% warrants a supportive review.",
    },
    "assessment_average": {
        "threshold": 60.0,
        "direction": "below",
        "weight": 35,
        "domain": "academics",
        "rationale": "An assessment average below 60 warrants academic review.",
    },
    "assignments_completed": {
        "threshold": 6.0,
        "direction": "below",
        "weight": 15,
        "domain": "academics",
        "rationale": "Fewer than 6 completed assignments warrants checking workload and support needs.",
    },
    "pending_lab_submissions": {
        "threshold": 2.0,
        "direction": "at_least",
        "weight": 15,
        "domain": "faculty_feedback",
        "rationale": "Two or more pending lab submissions warrant a faculty check-in.",
    },
}


def _as_utc(value: datetime) -> datetime:
    """Interpret naive SQLite datetimes as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def assess_academic_support(
    db: Session,
    student_id: int,
    *,
    now: datetime | None = None,
) -> RiskAssessment:
    """Calculate and persist a transparent academic-support review."""
    student = db.get(Student, student_id)
    if student is None:
        raise ValueError("Student not found.")

    consent = db.scalar(
        select(StudentConsent)
        .where(
            StudentConsent.student_id == student_id,
            StudentConsent.purpose == "academic_support",
        )
        .order_by(
            StudentConsent.recorded_at.desc(),
            StudentConsent.id.desc(),
        )
        .limit(1)
    )

    if consent is None or consent.status.strip().lower() != "granted":
        raise PermissionError(
            "Academic-support assessment requires explicitly granted consent."
        )

    assessed_at = _as_utc(now or datetime.now(timezone.utc))
    cutoff = assessed_at - timedelta(days=STALE_AFTER_DAYS)

    signals = db.scalars(
        select(StudentSignal)
        .where(
            StudentSignal.student_id == student_id,
            StudentSignal.purpose_category == "academic_support",
        )
        .order_by(
            StudentSignal.recorded_at.desc(),
            StudentSignal.id.desc(),
        )
    ).all()

    # Do not fall back to an older valid record if a newer one is missing.
    latest_by_name: dict[str, StudentSignal] = {}
    for signal in signals:
        latest_by_name.setdefault(signal.signal_name, signal)

    factors: list[dict] = []
    quality_notes: list[dict] = []
    points = 0
    available_weight = 0
    total_weight = sum(rule["weight"] for rule in THRESHOLDS.values())

    for signal_name, rule in THRESHOLDS.items():
        signal = latest_by_name.get(signal_name)

        if signal is None:
            quality_notes.append({
                "signal": signal_name,
                "quality_status": "missing",
                "note": "No observation is available; it was not scored.",
            })
            continue

        recorded_at = _as_utc(signal.recorded_at)
        quality = signal.quality_status.strip().lower()

        if quality != "valid":
            quality_notes.append({
                "signal": signal_name,
                "quality_status": quality,
                "recorded_at": recorded_at.isoformat(),
                "note": "Observation quality is not valid; it was not scored.",
            })
            continue

        if recorded_at > assessed_at:
            quality_notes.append({
                "signal": signal_name,
                "quality_status": "future_dated",
                "recorded_at": recorded_at.isoformat(),
                "note": "Observation is later than the assessment time; it was not scored.",
            })
            continue

        if recorded_at < cutoff:
            quality_notes.append({
                "signal": signal_name,
                "quality_status": "stale",
                "recorded_at": recorded_at.isoformat(),
                "note": "Observation is older than the freshness window; it was not scored.",
            })
            continue

        if signal.numeric_value is None:
            quality_notes.append({
                "signal": signal_name,
                "quality_status": "missing",
                "recorded_at": recorded_at.isoformat(),
                "note": "No numeric observation is available; it was not scored.",
            })
            continue

        value = float(signal.numeric_value)
        threshold = float(rule["threshold"])
        triggered = (
            value < threshold
            if rule["direction"] == "below"
            else value >= threshold
        )

        available_weight += rule["weight"]
        if triggered:
            points += rule["weight"]

        factors.append({
            "signal": signal_name,
            "domain": rule["domain"],
            "observed_value": value,
            "threshold": threshold,
            "direction": rule["direction"],
            "triggered": triggered,
            "weight": rule["weight"],
            "recorded_at": recorded_at.isoformat(),
            "rationale": rule["rationale"],
        })

    score = (
        round(points / available_weight * 100, 1)
        if available_weight
        else None
    )

    if score is None:
        risk_band = "needs_review"
        summary = (
            "Insufficient fresh, valid academic-support observations "
            "to calculate a review score."
        )
    elif score >= 60:
        risk_band = "priority_review"
        summary = (
            "Several configured rules were triggered. A staff member "
            "should review the context before deciding on support."
        )
    elif score >= 30:
        risk_band = "monitor"
        summary = (
            "Some configured rules were triggered. Consider a supportive "
            "staff check-in."
        )
    else:
        risk_band = "routine_review"
        summary = (
            "Few or no configured rules were triggered by available "
            "observations. This does not prove that no support is needed."
        )

    if available_weight < total_weight:
        quality_notes.append({
            "note": (
                "Only fresh, valid signals contribute to the score. "
                "Missing or stale signals reduce coverage, not student standing."
            ),
            "available_rule_weight": available_weight,
            "total_rule_weight": total_weight,
        })

    assessment = RiskAssessment(
        student_id=student_id,
        score=score,
        risk_band=risk_band,
        factor_breakdown=factors,
        data_quality_notes=quality_notes,
        rule_version=RULE_VERSION,
        summary=summary,
        assessed_at=assessed_at,
    )

    try:
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
    except Exception:
        db.rollback()
        raise

    return assessment
