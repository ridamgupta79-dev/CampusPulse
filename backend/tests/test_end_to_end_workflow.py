
from sqlalchemy import select
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from conftest import auth_headers
from app.models import (
    Intervention,
    InterventionEvent,
    InterventionOutcome,
    Recommendation,
    RiskAssessment,
    Student,
)

client = TestClient(app)
FACULTY = auth_headers("faculty")


def test_student_support_workflow_end_to_end():
    # Find the seeded demo student without modifying the seed data.
    with SessionLocal() as db:
        student = db.scalar(
            select(Student).where(
                Student.student_code == "CP-DEMO-0042"
            )
        )
        assert student is not None
        student_id = student.id

    assessment_id = None
    recommendation_id = None
    intervention_id = None

    try:
        # 1. Create a fresh, explainable assessment.
        response = client.post(
            f"/api/students/{student_id}/assessments/academic-support",
            headers=FACULTY,
        )
        assert response.status_code == 200, response.text

        assessment_id = response.json()["id"]
        assert response.json()["factor_breakdown"]

        # 2. Generate a proposed recommendation.
        response = client.post(
            f"/api/students/{student_id}/assessments/"
            f"{assessment_id}/recommendation",
            headers=FACULTY,
        )
        assert response.status_code == 200, response.text

        recommendation = response.json()
        recommendation_id = recommendation["id"]

        assert recommendation["status"] == "proposed"
        assert recommendation["created"] is True

        # 3. Human review: approve the recommendation.
        response = client.post(
            f"/api/recommendations/{recommendation_id}/review",
            headers=FACULTY,
            json={
                "decision": "approved",
                "reason": "Reviewed the evidence for this demo case.",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "approved"

        # 4. Assign the intervention to a named owner.
        response = client.post(
            f"/api/recommendations/{recommendation_id}/interventions",
            headers=FACULTY,
            json={
                "assigned_role": "faculty",
                "assigned_owner": "Workflow Integration Test",
                "supporting_role": "mentor",
                "due_date": "2026-12-20T17:00:00",
                "priority": "high",
            },
        )
        assert response.status_code == 201, response.text

        intervention = response.json()
        intervention_id = intervention["id"]
        assert intervention["status"] == "assigned"

        # 5. Mark work as started.
        response = client.patch(
            f"/api/interventions/{intervention_id}/status",
            headers=FACULTY,
            json={"status": "in_progress"},
        )
        assert response.status_code == 200, response.text

        # Record a follow-up note.
        response = client.post(
            f"/api/interventions/{intervention_id}/follow-up",
            headers=FACULTY,
            json={
                "note": (
                    "Temporary integration-test follow-up; "
                    "no real student interaction occurred."
                )
            },
        )
        assert response.status_code == 200, response.text

        # 6. Record a clearly illustrative outcome measurement.
        response = client.post(
            f"/api/interventions/{intervention_id}/outcomes",
            headers=FACULTY,
            json={
                "metric_name": "assessment_average",
                "baseline_value": 52,
                "baseline_date": "2026-10-12T00:00:00",
                "follow_up_value": 56,
                "follow_up_date": "2026-10-13T00:00:00",
                "classification": "improved",
                "outcome_note": (
                    "Synthetic integration-test values only; "
                    "not evidence of intervention effectiveness."
                ),
                "evidence_quality": "low",
            },
        )
        assert response.status_code == 201, response.text

        # Verify persisted records and audit history.
        with SessionLocal() as db:
            saved_recommendation = db.get(
                Recommendation, recommendation_id
            )
            saved_intervention = db.get(
                Intervention, intervention_id
            )
            assert saved_recommendation is not None
            assert saved_recommendation.status == "approved"
            assert saved_intervention is not None
            assert saved_intervention.status == "measured"

            outcomes = db.scalars(
                select(InterventionOutcome).where(
                    InterventionOutcome.intervention_id
                    == intervention_id
                )
            ).all()
            assert len(outcomes) == 1
            assert outcomes[0].baseline_value == 52
            assert outcomes[0].follow_up_value == 56

            events = db.scalars(
                select(InterventionEvent).where(
                    InterventionEvent.intervention_id
                    == intervention_id
                )
            ).all()
            event_types = {event.event_type for event in events}

            assert "assigned" in event_types
            assert "follow_up_recorded" in event_types
            assert "outcome_recorded" in event_types
            assert "status_changed" in event_types

    finally:
        # Remove only records created by this test.
        with SessionLocal() as db:
            if intervention_id is not None:
                outcomes = db.scalars(
                    select(InterventionOutcome).where(
                        InterventionOutcome.intervention_id
                        == intervention_id
                    )
                ).all()
                for item in outcomes:
                    db.delete(item)

                events = db.scalars(
                    select(InterventionEvent).where(
                        InterventionEvent.intervention_id
                        == intervention_id
                    )
                ).all()
                for item in events:
                    db.delete(item)

                intervention = db.get(
                    Intervention, intervention_id
                )
                if intervention is not None:
                    db.delete(intervention)

            if recommendation_id is not None:
                recommendation = db.get(
                    Recommendation, recommendation_id
                )
                if recommendation is not None:
                    db.delete(recommendation)

            if assessment_id is not None:
                assessment = db.get(
                    RiskAssessment, assessment_id
                )
                if assessment is not None:
                    db.delete(assessment)

            db.commit()
