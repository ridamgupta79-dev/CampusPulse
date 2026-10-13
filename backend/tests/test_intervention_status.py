
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from conftest import auth_headers
from app.models.intervention import Intervention
from app.models.recommendation import Recommendation

client = TestClient(app)


def test_assigned_intervention_can_start_work():
    db = SessionLocal()
    intervention_id = None

    try:
        recommendation = db.get(Recommendation, 1)
        assert recommendation is not None

        intervention = Intervention(
            student_id=recommendation.student_id,
            recommendation_id=None,
            intervention_type="status_test",
            description="Temporary status-transition test",
            assigned_role="faculty",
            assigned_owner="Status Test Owner",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            status="assigned",
            priority="medium",
        )
        db.add(intervention)
        db.commit()
        db.refresh(intervention)
        intervention_id = intervention.id

        response = client.patch(
            f"/api/interventions/{intervention_id}/status",
            headers=auth_headers("faculty"),
            json={"status": "in_progress"},
        )

        assert response.status_code == 200, response.text
        assert response.json()["status"] == "in_progress"

    finally:
        if intervention_id is not None:
            db.rollback()

            from sqlalchemy import select
            from app.models.intervention_event import InterventionEvent

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


def test_completed_intervention_cannot_be_reopened():
    db = SessionLocal()
    intervention_id = None

    try:
        recommendation = db.get(Recommendation, 1)
        assert recommendation is not None

        intervention = Intervention(
            student_id=recommendation.student_id,
            recommendation_id=None,
            intervention_type="status_test",
            description="Temporary completed intervention",
            assigned_role="faculty",
            assigned_owner="Status Test Owner",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            status="completed",
            priority="medium",
        )
        db.add(intervention)
        db.commit()
        db.refresh(intervention)
        intervention_id = intervention.id

        response = client.patch(
            f"/api/interventions/{intervention_id}/status",
            headers=auth_headers("faculty"),
            json={"status": "in_progress"},
        )

        assert response.status_code == 409

    finally:
        if intervention_id is not None:
            db.rollback()

            intervention = db.get(Intervention, intervention_id)
            if intervention is not None:
                db.delete(intervention)
                db.commit()

        db.close()


def test_cancellation_requires_a_reason():
    db = SessionLocal()
    intervention_id = None

    try:
        recommendation = db.get(Recommendation, 1)
        assert recommendation is not None

        intervention = Intervention(
            student_id=recommendation.student_id,
            recommendation_id=None,
            intervention_type="status_test",
            description="Temporary cancellation test",
            assigned_role="faculty",
            assigned_owner="Status Test Owner",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            status="assigned",
            priority="medium",
        )
        db.add(intervention)
        db.commit()
        db.refresh(intervention)
        intervention_id = intervention.id

        response = client.patch(
            f"/api/interventions/{intervention_id}/status",
            headers=auth_headers("faculty"),
            json={"status": "cancelled"},
        )

        assert response.status_code == 422

    finally:
        if intervention_id is not None:
            db.rollback()

            from sqlalchemy import select
            from app.models.intervention_event import InterventionEvent

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
