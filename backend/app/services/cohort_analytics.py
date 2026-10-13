
"""Privacy-conscious cohort-level student-success analytics."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.intervention import Intervention
from app.models.intervention_outcome import InterventionOutcome
from app.models.risk_assessment import RiskAssessment
from app.models.student import Student
from app.models.student_signal import StudentSignal


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Treat SQLite's naive datetimes as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_cohort_analytics(
    db: Session,
    cohort: str | None = None,
    stale_after_days: int = 30,
) -> dict:
    """Build aggregate counts without returning individual student records."""
    if stale_after_days < 1:
        raise ValueError("stale_after_days must be at least 1.")

    student_query = select(Student)
    if cohort:
        student_query = student_query.where(Student.cohort == cohort)

    students = db.scalars(student_query).all()
    student_ids = {student.id for student in students}
    student_count = len(student_ids)

    assessments = db.scalars(
        select(RiskAssessment)
        .where(RiskAssessment.student_id.in_(student_ids))
        .order_by(RiskAssessment.assessed_at.desc(), RiskAssessment.id.desc())
    ).all() if student_ids else []

    latest_assessment_by_student: dict[int, RiskAssessment] = {}
    for assessment in assessments:
        latest_assessment_by_student.setdefault(
            assessment.student_id,
            assessment,
        )

    risk_distribution: dict[str, int] = {}
    for assessment in latest_assessment_by_student.values():
        band = assessment.risk_band
        risk_distribution[band] = risk_distribution.get(band, 0) + 1

    interventions = db.scalars(
        select(Intervention).where(
            Intervention.student_id.in_(student_ids)
        )
    ).all() if student_ids else []

    now = _utc_now()
    intervention_status_counts: dict[str, int] = {}
    overdue_count = 0

    for intervention in interventions:
        status = intervention.status
        intervention_status_counts[status] = (
            intervention_status_counts.get(status, 0) + 1
        )

        if (
            status not in {"completed", "cancelled"}
            and _as_utc(intervention.due_date) < now
        ):
            overdue_count += 1

    intervention_ids = {item.id for item in interventions}
    outcomes = db.scalars(
        select(InterventionOutcome).where(
            InterventionOutcome.intervention_id.in_(intervention_ids)
        )
    ).all() if intervention_ids else []

    outcome_evidence_counts: dict[str, int] = {}
    for outcome in outcomes:
        quality = outcome.evidence_quality
        outcome_evidence_counts[quality] = (
            outcome_evidence_counts.get(quality, 0) + 1
        )

    signals = db.scalars(
        select(StudentSignal).where(
            StudentSignal.student_id.in_(student_ids)
        )
    ).all() if student_ids else []

    stale_cutoff = now.timestamp() - stale_after_days * 24 * 60 * 60
    missing_signal_count = sum(
        1 for signal in signals
        if signal.quality_status.strip().lower() == "missing"
    )
    stale_signal_count = sum(
        1 for signal in signals
        if (
            signal.quality_status.strip().lower() == "stale"
            or (
                signal.quality_status.strip().lower() == "valid"
                and _as_utc(signal.recorded_at).timestamp() < stale_cutoff
            )
        )
    )

    return {
        "cohort": cohort,
        "generated_at": now.isoformat(),
        "stale_after_days": stale_after_days,
        "student_count": student_count,
        "assessment_coverage": {
            "assessed_students": len(latest_assessment_by_student),
            "students_without_assessment": (
                student_count - len(latest_assessment_by_student)
            ),
        },
        "risk_distribution": risk_distribution,
        "intervention_workload": {
            "total": len(interventions),
            "by_status": intervention_status_counts,
            "overdue_open_interventions": overdue_count,
        },
        "outcome_coverage": {
            "recorded_outcomes": len(outcomes),
            "interventions_with_outcomes": len({
                outcome.intervention_id for outcome in outcomes
            }),
            "by_evidence_quality": outcome_evidence_counts,
        },
        "data_quality": {
            "signals_examined": len(signals),
            "missing_signals": missing_signal_count,
            "stale_signals": stale_signal_count,
            "note": (
                "Missing and stale signals are data-quality indicators, "
                "not evidence that a student is at risk."
            ),
        },
        "interpretation_note": (
            "These are descriptive cohort aggregates. They do not establish "
            "that an intervention caused a measured outcome."
        ),
    }
