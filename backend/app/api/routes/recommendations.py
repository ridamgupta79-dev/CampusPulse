
"""API endpoints for recommendation review and intervention creation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import (
    can_review_recommendation,
    get_current_staff_role,
)
from app.db.session import get_db
from app.models.intervention import Intervention
from app.models.intervention_event import InterventionEvent
from app.models.recommendation import Recommendation
from app.schemas.intervention_workflow import (
    InterventionAssignmentRequest,
    RecommendationReviewRequest,
)
from app.services.intervention_workflow import review_recommendation
from app.models.student import Student


router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"],
)



@router.get("")
def list_recommendations(
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> list[dict]:
    """List recommendations visible to the current demo role."""
    statement = (
        select(Recommendation, Student)
        .join(Student, Student.id == Recommendation.student_id)
        .order_by(Recommendation.created_at.desc())
    )

    records = db.execute(statement).all()

    return [
        {
            "id": recommendation.id,
            "student_id": recommendation.student_id,
            "student_name": student.full_name,
            "student_code": student.student_code,
            "assessment_id": recommendation.assessment_id,
            "intervention_type": recommendation.intervention_type,
            "rationale": recommendation.rationale,
            "contributing_signals": recommendation.contributing_signals,
            "intended_role": recommendation.intended_role,
            "suggested_next_step": recommendation.suggested_next_step,
            "priority": recommendation.priority,
            "status": recommendation.status,
            "decision_reason": recommendation.decision_reason,
            "created_at": recommendation.created_at,
            "updated_at": recommendation.updated_at,
        }
        for recommendation, student in records
        if can_review_recommendation(
            actor_role=role,
            intended_role=recommendation.intended_role,
        )
    ]

@router.post("/{recommendation_id}/review")
def review_recommendation_endpoint(
    recommendation_id: int,
    payload: RecommendationReviewRequest,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> dict:
    """Review a proposed recommendation using demo-role permissions."""

    recommendation = db.get(Recommendation, recommendation_id)

    if recommendation is None:
        raise HTTPException(
            status_code=404,
            detail="Recommendation not found.",
        )

    if not can_review_recommendation(
        actor_role=role,
        intended_role=recommendation.intended_role,
    ):
        raise HTTPException(
            status_code=403,
            detail="Your role cannot review this recommendation.",
        )

    reviewed = review_recommendation(
        db=db,
        recommendation_id=recommendation_id,
        decision=payload.decision,
        actor_role=role,
        actor_label=f"{role.title()} Demo Actor",
        reason=payload.reason,
    )

    return {
        "id": reviewed.id,
        "student_id": reviewed.student_id,
        "status": reviewed.status,
        "decision_reason": reviewed.decision_reason,
        "message": "Recommendation review recorded.",
    }


@router.post("/{recommendation_id}/interventions", status_code=201)
def create_intervention_endpoint(
    recommendation_id: int,
    payload: InterventionAssignmentRequest,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> dict:
    """Create and assign an intervention from an approved recommendation."""

    recommendation = db.get(Recommendation, recommendation_id)

    if recommendation is None:
        raise HTTPException(
            status_code=404,
            detail="Recommendation not found.",
        )

    if not can_review_recommendation(
        actor_role=role,
        intended_role=recommendation.intended_role,
    ):
        raise HTTPException(
            status_code=403,
            detail="Your role cannot assign this recommendation.",
        )

    if recommendation.status != "approved":
        raise HTTPException(
            status_code=409,
            detail="Only approved recommendations can create interventions.",
        )

    existing_id = db.scalar(
        select(Intervention.id).where(
            Intervention.recommendation_id == recommendation_id
        )
    )
    if existing_id is not None:
        raise HTTPException(
            status_code=409,
            detail="An intervention already exists for this recommendation.",
        )

    intervention = Intervention(
        student_id=recommendation.student_id,
        recommendation_id=recommendation.id,
        intervention_type=recommendation.intervention_type,
        description=(
            recommendation.suggested_next_step
            or recommendation.rationale
        ),
        assigned_role=payload.assigned_role,
        assigned_owner=payload.assigned_owner,
        supporting_role=payload.supporting_role,
        due_date=payload.due_date,
        status="assigned",
        priority=payload.priority,
    )

    try:
        db.add(intervention)
        db.flush()

        event = InterventionEvent(
            intervention_id=intervention.id,
            event_type="assigned",
            actor_role=role,
            actor_label=f"{role.title()} Demo Actor",
            note=(
                f"Intervention assigned to {payload.assigned_owner} "
                f"({payload.assigned_role})."
            ),
        )
        db.add(event)
        db.commit()
        db.refresh(intervention)

    except Exception:
        db.rollback()
        raise

    return {
        "id": intervention.id,
        "student_id": intervention.student_id,
        "recommendation_id": intervention.recommendation_id,
        "intervention_type": intervention.intervention_type,
        "assigned_role": intervention.assigned_role,
        "assigned_owner": intervention.assigned_owner,
        "supporting_role": intervention.supporting_role,
        "due_date": intervention.due_date,
        "status": intervention.status,
        "priority": intervention.priority,
        "message": "Intervention created and assigned.",
    }
