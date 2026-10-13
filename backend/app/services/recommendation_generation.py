
"""Generate explainable support recommendations from saved assessments."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Recommendation, RiskAssessment


def generate_recommendation(
    db: Session,
    assessment_id: int,
) -> tuple[Recommendation, bool]:
    """Create a proposed recommendation from an existing assessment.

    Returns (recommendation, created).
    Existing recommendations for the same assessment are preserved.
    """
    assessment = db.get(RiskAssessment, assessment_id)

    if assessment is None:
        raise HTTPException(
            status_code=404,
            detail="Risk assessment not found.",
        )

    existing = db.scalar(
        select(Recommendation)
        .where(Recommendation.assessment_id == assessment_id)
        .order_by(Recommendation.id.asc())
        .limit(1)
    )

    if existing is not None:
        return existing, False

    factors = assessment.factor_breakdown or []

    triggered_factors = [
        factor
        for factor in factors
        if isinstance(factor, dict)
        and factor.get("triggered") is True
        and factor.get("signal")
    ]

    if assessment.score is None or not triggered_factors:
        raise HTTPException(
            status_code=422,
            detail=(
                "This assessment does not contain sufficient "
                "triggered evidence for a recommendation."
            ),
        )

    signal_names = [
        factor["signal"] for factor in triggered_factors
    ]

    explanations = [
        (
            f"{factor['signal']}: observed value "
            f"{factor.get('observed_value')}; "
            f"configured threshold {factor.get('threshold')}. "
            f"{factor.get('rationale', '')}"
        ).strip()
        for factor in triggered_factors
    ]

    rationale = (
        "Supportive staff review suggested by the following "
        "configured assessment rules: "
        + " ".join(explanations)
        + " These rules support human review; they do not establish "
        "a diagnosis or determine what action a student needs."
    )

    recommendation = Recommendation(
        student_id=assessment.student_id,
        assessment_id=assessment.id,
        intervention_type="academic_support_check_in",
        rationale=rationale,
        contributing_signals=signal_names,
        intended_role="faculty",
        suggested_next_step=(
            "Review the contributing observations with the student, "
            "verify their context, and agree on an appropriate support "
            "plan before assigning an intervention."
        ),
        priority=(
            "high" if assessment.score >= 60 else "medium"
        ),
        status="proposed",
    )

    try:
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)
        return recommendation, True
    except Exception:
        db.rollback()
        raise
