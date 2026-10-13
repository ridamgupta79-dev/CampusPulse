
"""Business rules for recommendation review and intervention follow-up."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.intervention import Intervention
from app.models.intervention_event import InterventionEvent
from app.models.recommendation import Recommendation
from app.models.intervention_outcome import InterventionOutcome
from app.schemas.intervention_workflow import InterventionOutcomeRequest


RECOMMENDATION_DECISIONS = frozenset({"approved", "declined"})

INTERVENTION_STATUSES = frozenset({
    "approved",
    "assigned",
    "in_progress",
    "follow_up_recorded",
    "measured",
    "completed",
    "cancelled",
})

ALLOWED_STATUS_TRANSITIONS = {
    "approved": frozenset({"assigned", "cancelled"}),
    "assigned": frozenset({"in_progress", "cancelled"}),
    "in_progress": frozenset({"follow_up_recorded", "completed", "cancelled"}),
    "follow_up_recorded": frozenset({
        "in_progress",
        "measured",
        "completed",
        "cancelled",
    }),
    "measured": frozenset({"in_progress", "completed", "cancelled"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}


def validate_recommendation_decision(
    decision: str,
    reason: str | None = None,
) -> str:
    """Validate a human review decision."""
    normalized_decision = decision.strip().lower()

    if normalized_decision not in RECOMMENDATION_DECISIONS:
        raise HTTPException(
            status_code=422,
            detail="Decision must be 'approved' or 'declined'.",
        )

    if normalized_decision == "declined" and (
        not reason or not reason.strip()
    ):
        raise HTTPException(
            status_code=422,
            detail="A reason is required when declining a recommendation.",
        )

    return normalized_decision


def validate_intervention_status(status: str) -> str:
    """Validate that an intervention status is recognized."""
    normalized_status = status.strip().lower()

    if normalized_status not in INTERVENTION_STATUSES:
        raise HTTPException(
            status_code=422,
            detail="Unrecognized intervention status.",
        )

    return normalized_status


def review_recommendation(
    db: Session,
    recommendation_id: int,
    decision: str,
    actor_role: str,
    actor_label: str,
    reason: str | None = None,
) -> Recommendation:
    """Record a human decision on a proposed recommendation."""
    normalized_decision = validate_recommendation_decision(
        decision,
        reason,
    )

    if not actor_role.strip() or not actor_label.strip():
        raise HTTPException(
            status_code=422,
            detail="Actor role and label are required.",
        )

    try:
        recommendation = db.scalar(
            select(Recommendation)
            .where(Recommendation.id == recommendation_id)
            .with_for_update()
        )

        if recommendation is None:
            raise HTTPException(
                status_code=404,
                detail="Recommendation not found.",
            )

        if recommendation.status != "proposed":
            raise HTTPException(
                status_code=409,
                detail="Only proposed recommendations can be reviewed.",
            )

        existing_intervention = db.scalar(
            select(Intervention.id).where(
                Intervention.recommendation_id == recommendation_id
            )
        )

        if existing_intervention is not None:
            raise HTTPException(
                status_code=409,
                detail="This recommendation already has an intervention.",
            )

        recommendation.status = normalized_decision
        recommendation.decision_reason = (
            reason.strip() if reason and reason.strip() else None
        )

        db.commit()
        db.refresh(recommendation)
        return recommendation

    except Exception:
        db.rollback()
        raise


def record_intervention_follow_up(
    db: Session,
    intervention_id: int,
    actor_role: str,
    actor_label: str,
    note: str,
) -> tuple[Intervention, InterventionEvent]:
    """Record a human follow-up note and preserve event history."""
    if not actor_role.strip() or not actor_label.strip():
        raise HTTPException(
            status_code=422,
            detail="Actor role and label are required.",
        )

    normalized_note = note.strip()
    if not normalized_note:
        raise HTTPException(
            status_code=422,
            detail="A follow-up note is required.",
        )

    try:
        intervention = db.scalar(
            select(Intervention)
            .where(Intervention.id == intervention_id)
            .with_for_update()
        )

        if intervention is None:
            raise HTTPException(
                status_code=404,
                detail="Intervention not found.",
            )

        if intervention.status not in {"assigned", "in_progress"}:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Follow-up can only be recorded for assigned "
                    "or in-progress interventions."
                ),
            )

        intervention.status = "follow_up_recorded"

        event = InterventionEvent(
            intervention_id=intervention.id,
            event_type="follow_up_recorded",
            actor_role=actor_role.strip().lower(),
            actor_label=actor_label.strip(),
            note=normalized_note,
        )

        db.add(event)
        db.commit()
        db.refresh(intervention)
        db.refresh(event)

        return intervention, event

    except Exception:
        db.rollback()
        raise


def transition_intervention_status(
    db: Session,
    intervention_id: int,
    new_status: str,
    actor_role: str,
    actor_label: str,
    reason: str | None = None,
) -> tuple[Intervention, InterventionEvent]:
    """Apply an allowed status transition and record the reason."""
    normalized_status = validate_intervention_status(new_status)

    if not actor_role.strip() or not actor_label.strip():
        raise HTTPException(
            status_code=422,
            detail="Actor role and label are required.",
        )

    try:
        intervention = db.scalar(
            select(Intervention)
            .where(Intervention.id == intervention_id)
            .with_for_update()
        )

        if intervention is None:
            raise HTTPException(
                status_code=404,
                detail="Intervention not found.",
            )

        current_status = intervention.status
        allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, frozenset())

        if normalized_status not in allowed:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Cannot transition intervention from "
                    f"'{current_status}' to '{normalized_status}'."
                ),
            )

        if normalized_status == "cancelled" and (
            not reason or not reason.strip()
        ):
            raise HTTPException(
                status_code=422,
                detail="A reason is required to cancel an intervention.",
            )

        intervention.status = normalized_status

        event = InterventionEvent(
            intervention_id=intervention.id,
            event_type="status_changed",
            actor_role=actor_role.strip().lower(),
            actor_label=actor_label.strip(),
            note=reason.strip() if reason and reason.strip() else None,
            event_metadata={
                "from_status": current_status,
                "to_status": normalized_status,
            },
        )

        db.add(event)
        db.commit()
        db.refresh(intervention)
        db.refresh(event)

        return intervention, event

    except Exception:
        db.rollback()
        raise


def record_intervention_outcome(
    db: Session,
    intervention_id: int,
    payload: InterventionOutcomeRequest,
    actor_role: str,
    actor_label: str,
) -> tuple[InterventionOutcome, InterventionEvent]:
    """Persist an outcome measurement and its audit event."""

    if not actor_role.strip() or not actor_label.strip():
        raise HTTPException(
            status_code=422,
            detail="Actor role and label are required.",
        )

    try:
        intervention = db.scalar(
            select(Intervention)
            .where(Intervention.id == intervention_id)
            .with_for_update()
        )

        if intervention is None:
            raise HTTPException(
                status_code=404,
                detail="Intervention not found.",
            )

        if intervention.status in {"cancelled", "approved", "assigned"}:
            raise HTTPException(
                status_code=409,
                detail=(
                    "An outcome can only be recorded after work "
                    "has started or follow-up has been documented."
                ),
            )

        outcome = InterventionOutcome(
            intervention_id=intervention.id,
            metric_name=payload.metric_name,
            baseline_value=payload.baseline_value,
            baseline_date=payload.baseline_date,
            follow_up_value=payload.follow_up_value,
            follow_up_date=payload.follow_up_date,
            classification=payload.classification,
            outcome_note=payload.outcome_note,
            evidence_quality=payload.evidence_quality,
        )
        db.add(outcome)
        db.flush()

        event = InterventionEvent(
            intervention_id=intervention.id,
            event_type="outcome_recorded",
            actor_role=actor_role.strip().lower(),
            actor_label=actor_label.strip(),
            note=payload.outcome_note,
            event_metadata={
                "outcome_id": outcome.id,
                "metric_name": payload.metric_name,
                "classification": payload.classification,
                "evidence_quality": payload.evidence_quality,
            },
        )
        db.add(event)

        if payload.follow_up_value is not None:
            intervention.status = "measured"

        db.commit()
        db.refresh(outcome)
        db.refresh(event)

        return outcome, event

    except Exception:
        db.rollback()
        raise

