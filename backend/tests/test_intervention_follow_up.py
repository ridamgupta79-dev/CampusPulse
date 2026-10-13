
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from conftest import auth_headers
from app.models.intervention import Intervention
from app.models.intervention_event import InterventionEvent
from app.models.recommendation import Recommendation

client = TestClient(app)


def test_follow_up_records_note_and_event():
    db = SessionLocal()
    intervention_id = None

    try:
        recommendation = db.get(Recommendation, 1)
        assert recommendation is not None

        intervention = Intervention(
            student_id=recommendation.student_id,
            recommendation_id=None,
            intervention_type="follow_up_test",
            description="Temporary test intervention",
            assigned_role="faculty",
            assigned_owner="Follow-up Test Owner",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            status="assigned",
            priority="medium",
        )
        db.add(intervention)
        db.commit()
        db.refresh(intervention)
        intervention_id = intervention.id

        response = client.post(
            f"/api/interventions/{intervention_id}/follow-up",
            headers=auth_headers("faculty"),
            json={"note": "Student attended the scheduled support session."},
        )

        assert response.status_code == 200, response.text
        result = response.json()
        assert result["status"] == "follow_up_recorded"
        assert result["event_type"] == "follow_up_recorded"

        db.expire_all()
        saved_intervention = db.get(Intervention, intervention_id)
        assert saved_intervention is not None
        assert saved_intervention.status == "follow_up_recorded"

        events = db.scalars(
            select(InterventionEvent).where(
                InterventionEvent.intervention_id == intervention_id,
                InterventionEvent.event_type == "follow_up_recorded",
            )
        ).all()

        assert len(events) == 1
        assert events[0].note == (
            "Student attended the scheduled support session."
        )

    finally:
        if intervention_id is not None:
            db.rollback()
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
