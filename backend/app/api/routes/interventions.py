
"""API endpoints for intervention follow-up and status changes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import get_current_staff_role
from app.db.session import get_db
from app.models.intervention import Intervention
from app.schemas.intervention_workflow import (
    InterventionFollowUpRequest,
    InterventionStatusUpdateRequest,
)
from app.services.intervention_workflow import (
    record_intervention_follow_up,
    transition_intervention_status,
)
from app.schemas.intervention_workflow import (
    InterventionFollowUpRequest,
    InterventionOutcomeRequest,
    InterventionStatusUpdateRequest,
)
from app.services.intervention_workflow import (
    record_intervention_follow_up,
    record_intervention_outcome,
    transition_intervention_status,
)
from sqlalchemy import select
from app.models.student import Student
router = APIRouter(prefix="/interventions", tags=["Interventions"])


@router.get("")
def list_interventions(
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> list[dict]:
    """List interventions visible to the current demo role."""
    statement = (
        select(Intervention, Student)
        .join(Student, Student.id == Intervention.student_id)
        .order_by(Intervention.due_date.asc())
    )

    records = db.execute(statement).all()

    visible = []
    for intervention, student in records:
        permitted_roles = {
            intervention.assigned_role.strip().lower(),
            "hod",
        }
        if intervention.supporting_role:
            permitted_roles.add(intervention.supporting_role.strip().lower())

        if role not in permitted_roles:
            continue

        visible.append({
            "id": intervention.id,
            "student_id": intervention.student_id,
            "student_name": student.full_name,
            "student_code": student.student_code,
            "recommendation_id": intervention.recommendation_id,
            "intervention_type": intervention.intervention_type,
            "description": intervention.description,
            "assigned_role": intervention.assigned_role,
            "assigned_owner": intervention.assigned_owner,
            "supporting_role": intervention.supporting_role,
            "due_date": intervention.due_date,
            "status": intervention.status,
            "priority": intervention.priority,
            "override_reason": intervention.override_reason,
            "created_at": intervention.created_at,
            "updated_at": intervention.updated_at,
        })

    return visible

def ensure_intervention_access(
    intervention: Intervention,
    role: str,
) -> None:
    """Allow the assigned role, supporting role, or HOD to act."""
    permitted_roles = {
        intervention.assigned_role.strip().lower(),
        "hod",
    }

    if intervention.supporting_role:
        permitted_roles.add(intervention.supporting_role.strip().lower())

    if role not in permitted_roles:
        raise HTTPException(
            status_code=403,
            detail="Your role cannot update this intervention.",
        )


@router.post("/{intervention_id}/follow-up")
def record_follow_up_endpoint(
    intervention_id: int,
    payload: InterventionFollowUpRequest,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> dict:
    """Record a follow-up note for an assigned intervention."""
    intervention = db.get(Intervention, intervention_id)

    if intervention is None:
        raise HTTPException(
            status_code=404,
            detail="Intervention not found.",
        )

    ensure_intervention_access(intervention, role)

    updated, event = record_intervention_follow_up(
        db=db,
        intervention_id=intervention_id,
        actor_role=role,
        actor_label=f"{role.title()} Demo Actor",
        note=payload.note,
    )

    return {
        "intervention_id": updated.id,
        "status": updated.status,
        "event_id": event.id,
        "event_type": event.event_type,
        "message": "Follow-up recorded.",
    }


@router.patch("/{intervention_id}/status")
def update_intervention_status_endpoint(
    intervention_id: int,
    payload: InterventionStatusUpdateRequest,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> dict:
    """Apply an allowed intervention status transition."""
    intervention = db.get(Intervention, intervention_id)

    if intervention is None:
        raise HTTPException(
            status_code=404,
            detail="Intervention not found.",
        )

    ensure_intervention_access(intervention, role)

    updated, event = transition_intervention_status(
        db=db,
        intervention_id=intervention_id,
        new_status=payload.status,
        actor_role=role,
        actor_label=f"{role.title()} Demo Actor",
        reason=payload.reason,
    )

    return {
        "intervention_id": updated.id,
        "status": updated.status,
        "event_id": event.id,
        "event_type": event.event_type,
        "message": "Intervention status updated.",
    }


@router.post("/{intervention_id}/outcomes", status_code=201)
def record_intervention_outcome_endpoint(
    intervention_id: int,
    payload: InterventionOutcomeRequest,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> dict:
    """Record a measured or documented intervention outcome."""

    intervention = db.get(Intervention, intervention_id)

    if intervention is None:
        raise HTTPException(
            status_code=404,
            detail="Intervention not found.",
        )

    ensure_intervention_access(intervention, role)

    outcome, event = record_intervention_outcome(
        db=db,
        intervention_id=intervention_id,
        payload=payload,
        actor_role=role,
        actor_label=f"{role.title()} Demo Actor",
    )

    return {
        "outcome_id": outcome.id,
        "intervention_id": outcome.intervention_id,
        "metric_name": outcome.metric_name,
        "baseline_value": outcome.baseline_value,
        "follow_up_value": outcome.follow_up_value,
        "classification": outcome.classification,
        "evidence_quality": outcome.evidence_quality,
        "event_id": event.id,
        "event_type": event.event_type,
        "message": "Intervention outcome recorded.",
    }

