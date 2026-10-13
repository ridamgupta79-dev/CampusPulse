
from fastapi.testclient import TestClient

from app.main import app
from conftest import auth_headers
from app.db.session import SessionLocal
from app.models.recommendation import Recommendation
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.intervention import Intervention
from app.models.intervention_event import InterventionEvent
from app.models.recommendation import Recommendation

client = TestClient(app)


def test_review_endpoint_requires_authentication():
    response = client.post(
        "/api/recommendations/1/review",
        json={"decision": "approved"},
    )

    assert response.status_code == 401


def test_review_endpoint_rejects_invalid_decision():
    response = client.post(
        "/api/recommendations/1/review",
        headers=auth_headers("hod"),
        json={"decision": "pending"},
    )

    assert response.status_code == 422


def test_review_endpoint_rejects_unknown_recommendation():
    response = client.post(
        "/api/recommendations/999999/review",
        headers=auth_headers("hod"),
        json={
            "decision": "approved",
        },
    )

    assert response.status_code == 404


def test_wrong_role_cannot_review_faculty_recommendation():
    response = client.post(
        "/api/recommendations/1/review",
        headers=auth_headers("finance"),
        json={"decision": "approved"},
    )

    # Recommendation 1 is the seeded faculty recommendation.
    assert response.status_code == 403


def test_declining_without_reason_is_rejected():
    response = client.post(
        "/api/recommendations/1/review",
        headers=auth_headers("faculty"),
        json={"decision": "declined"},
    )

    assert response.status_code == 422

def test_successful_approval_preserves_seeded_recommendation():
    db = SessionLocal()
    test_recommendation = None

    try:
        source = db.get(Recommendation, 1)
        assert source is not None, "Seeded recommendation 1 must exist."
        assert source.intended_role == "faculty"

        test_recommendation = Recommendation(
            student_id=source.student_id,
            assessment_id=source.assessment_id,
            intervention_type=source.intervention_type,
            rationale=source.rationale,
            contributing_signals=source.contributing_signals,
            intended_role=source.intended_role,
            suggested_next_step=source.suggested_next_step,
            priority=source.priority,
            status="proposed",
        )
        db.add(test_recommendation)
        db.commit()
        db.refresh(test_recommendation)

        test_id = test_recommendation.id

        response = client.post(
            f"/api/recommendations/{test_id}/review",
            headers=auth_headers("faculty"),
            json={"decision": "approved"},
        )

        assert response.status_code == 200, response.text
        assert response.json()["status"] == "approved"

    finally:
        if test_recommendation is not None:
            db.rollback()
            record = db.get(Recommendation, test_recommendation.id)
            if record is not None:
                db.delete(record)
                db.commit()

        db.close()


def test_intervention_creation_requires_authentication():
    response = client.post(
        "/api/recommendations/1/interventions",
        json={
            "assigned_role": "faculty",
            "assigned_owner": "Faculty Test",
            "due_date": "2026-10-20T17:00:00",
            "priority": "medium",
        },
    )

    assert response.status_code == 401


def test_intervention_creation_rejects_unknown_recommendation():
    response = client.post(
        "/api/recommendations/999999/interventions",
        headers=auth_headers("hod"),
        json={
            "assigned_role": "faculty",
            "assigned_owner": "Faculty Test",
            "due_date": "2026-10-20T17:00:00",
            "priority": "medium",
        },
    )

    assert response.status_code == 404


def test_intervention_creation_rejects_unapproved_recommendation():
    from unittest.mock import patch

    from app.models.recommendation import Recommendation

    with patch.object(
        Recommendation,
        "status",
        new="proposed",
    ):
        response = client.post(
            "/api/recommendations/1/interventions",
            headers=auth_headers("faculty"),
            json={
                "assigned_role": "faculty",
                "assigned_owner": "Faculty Test",
                "due_date": "2026-10-20T17:00:00",
                "priority": "medium",
            },
        )

    assert response.status_code == 409


def test_approved_recommendation_can_be_assigned_and_records_event():
    db = SessionLocal()
    recommendation_id = None

    try:
        source = db.get(Recommendation, 1)
        assert source is not None
        assert source.intended_role == "faculty"

        temporary_recommendation = Recommendation(
            student_id=source.student_id,
            assessment_id=source.assessment_id,
            intervention_type=source.intervention_type,
            rationale=source.rationale,
            contributing_signals=source.contributing_signals,
            intended_role=source.intended_role,
            suggested_next_step=source.suggested_next_step,
            priority=source.priority,
            status="proposed",
        )
        db.add(temporary_recommendation)
        db.commit()
        db.refresh(temporary_recommendation)
        recommendation_id = temporary_recommendation.id

        approval = client.post(
            f"/api/recommendations/{recommendation_id}/review",
            headers=auth_headers("faculty"),
            json={"decision": "approved"},
        )
        assert approval.status_code == 200, approval.text

        assignment = client.post(
            f"/api/recommendations/{recommendation_id}/interventions",
            headers=auth_headers("faculty"),
            json={
                "assigned_role": "faculty",
                "assigned_owner": "Faculty Workflow Test",
                "supporting_role": "mentor",
                "due_date": "2026-10-20T17:00:00",
                "priority": "high",
            },
        )

        assert assignment.status_code == 201, assignment.text

        result = assignment.json()
        assert result["recommendation_id"] == recommendation_id
        assert result["assigned_owner"] == "Faculty Workflow Test"
        assert result["assigned_role"] == "faculty"
        assert result["status"] == "assigned"
        assert result["priority"] == "high"

        events = db.scalars(
            select(InterventionEvent).where(
                InterventionEvent.intervention_id == result["id"]
            )
        ).all()

        assert any(event.event_type == "assigned" for event in events)

    finally:
        if recommendation_id is not None:
            db.rollback()

            interventions = db.scalars(
                select(Intervention).where(
                    Intervention.recommendation_id == recommendation_id
                )
            ).all()

            for intervention in interventions:
                events = db.scalars(
                    select(InterventionEvent).where(
                        InterventionEvent.intervention_id == intervention.id
                    )
                ).all()

                for event in events:
                    db.delete(event)

                db.delete(intervention)

            recommendation = db.get(Recommendation, recommendation_id)
            if recommendation is not None:
                db.delete(recommendation)

            db.commit()

        db.close()

def test_list_recommendations_requires_authentication():
    response = client.get("/api/recommendations")
    assert response.status_code == 401


def test_list_recommendations_returns_visible_records():
    response = client.get(
        "/api/recommendations",
        headers=auth_headers("faculty"),
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)

    for item in response.json():
        assert "student_name" in item
        assert "student_code" in item
        assert "status" in item
        assert "priority" in item



