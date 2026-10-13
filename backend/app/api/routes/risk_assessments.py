
"""Role-protected academic-support assessment endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import get_current_staff_role
from app.db.session import get_db
from app.models import RiskAssessment
from app.services.risk_assessment import assess_academic_support
from app.services.recommendation_generation import (
    generate_recommendation,
)

router = APIRouter(
    prefix="/students",
    tags=["Risk Assessments"],
)

ALLOWED_ASSESSMENT_ROLES = {"faculty", "mentor", "hod"}


def serialize_assessment(item: RiskAssessment) -> dict:
    return {
        "id": item.id,
        "student_id": item.student_id,
        "score": item.score,
        "risk_band": item.risk_band,
        "factor_breakdown": item.factor_breakdown,
        "data_quality_notes": item.data_quality_notes,
        "rule_version": item.rule_version,
        "summary": item.summary,
        "assessed_at": item.assessed_at.isoformat(),
    }


@router.post("/{student_id}/assessments/academic-support")
def create_academic_support_assessment(
    student_id: int,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> dict:
    """Run and persist an academic-support assessment."""
    if role not in ALLOWED_ASSESSMENT_ROLES:
        raise HTTPException(
            status_code=403,
            detail="This role cannot initiate academic-support assessments.",
        )

    try:
        assessment = assess_academic_support(db, student_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return serialize_assessment(assessment)


@router.post("/{student_id}/assessments/{assessment_id}/recommendation")
def create_assessment_recommendation(
    student_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> dict:
    """Generate a proposed recommendation from a saved assessment."""
    if role not in ALLOWED_ASSESSMENT_ROLES:
        raise HTTPException(
            status_code=403,
            detail="This role cannot generate academic-support recommendations.",
        )

    assessment = db.get(RiskAssessment, assessment_id)

    if assessment is None or assessment.student_id != student_id:
        raise HTTPException(
            status_code=404,
            detail="Assessment not found for this student.",
        )

    recommendation, created = generate_recommendation(
        db=db,
        assessment_id=assessment_id,
    )

    return {
        "id": recommendation.id,
        "student_id": recommendation.student_id,
        "assessment_id": recommendation.assessment_id,
        "intervention_type": recommendation.intervention_type,
        "rationale": recommendation.rationale,
        "contributing_signals": recommendation.contributing_signals,
        "intended_role": recommendation.intended_role,
        "suggested_next_step": recommendation.suggested_next_step,
        "priority": recommendation.priority,
        "status": recommendation.status,
        "created": created,
        "message": (
            "Recommendation created and awaits human review."
            if created
            else "An existing recommendation was preserved."
        ),
    }

