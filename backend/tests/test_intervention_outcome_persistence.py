
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from conftest import auth_headers
from app.models.intervention import Intervention
from app.models.intervention_event import InterventionEvent
from app.models.intervention_outcome import InterventionOutcome
from app.models.recommendation import Recommendation

client = TestClient(app)


def test_outcome_and_event_are_persisted_together():
    db = SessionLocal()
    intervention_id = None

    try:
        recommendation = db.get(Recommendation, 1)
        assert recommendation is not None

        intervention = Intervention(
            student_id=recommendation.student_id,
            recommendation_id=None,
            intervention_type="outcome_test",
            description="Temporary outcome persistence test",
            assigned_role="faculty",
            assigned_owner="Outcome Test Owner",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            status="in_progress",
            priority="medium",
        )
        db.add(intervention)
        db.commit()
        db.refresh(intervention)
        intervention_id = intervention.id

        response = client.post(
            f"/api/interventions/{intervention_id}/outcomes",
            headers=auth_headers("faculty"),
            json={
                "metric_name": "Assessment average",
                "baseline_value": 52,
                "baseline_date": "2026-10-08T10:00:00",
                "follow_up_value": 60,
                "follow_up_date": "2026-10-11T10:00:00",
                "classification": "improved",
                "evidence_quality": "medium",
                "outcome_note": "Illustrative measurement for testing.",
            },
        )

        assert response.status_code == 201, response.text
        result = response.json()
        assert result["metric_name"] == "Assessment average"
        assert result["baseline_value"] == 52
        assert result["follow_up_value"] == 60
        assert result["classification"] == "improved"
        assert result["event_type"] == "outcome_recorded"

        outcome = db.get(InterventionOutcome, result["outcome_id"])
        assert outcome is not None
        assert outcome.intervention_id == intervention_id

        event = db.get(InterventionEvent, result["event_id"])
        assert event is not None
        assert event.intervention_id == intervention_id
        assert event.event_type == "outcome_recorded"
        assert event.event_metadata["outcome_id"] == outcome.id

        db.expire_all()
        saved_intervention = db.get(Intervention, intervention_id)
        assert saved_intervention is not None
        assert saved_intervention.status == "measured"

    finally:
        if intervention_id is not None:
            db.rollback()

            outcomes = db.scalars(
                select(InterventionOutcome).where(
                    InterventionOutcome.intervention_id == intervention_id
                )
            ).all()
            for outcome in outcomes:
                db.delete(outcome)

            events = db.scalars(
                select(InterventionEvent).where(
                    InterventionEvent.intervention_id == intervention_id
                )
            ).all()
            for event in events:
                db.delete(event)

            intervention = db.get(Intervention, intervention_id)
            if intervention is not None:
                db.delete(intervention)

            db.commit()

        db.close()
