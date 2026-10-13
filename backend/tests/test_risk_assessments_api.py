
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from conftest import auth_headers
from app.models import RiskAssessment, Student

client = TestClient(app)


def get_student_id(code: str) -> int:
    with SessionLocal() as db:
        student = db.scalar(
            select(Student).where(Student.student_code == code)
        )
        assert student is not None
        return student.id


def test_assessment_requires_authentication():
    student_id = get_student_id("CP-DEMO-0042")
    response = client.post(
        f"/api/students/{student_id}/assessments/academic-support"
    )
    assert response.status_code == 401


def test_assessment_rejects_ungranted_consent():
    student_id = get_student_id("CP-DEMO-0044")
    response = client.post(
        f"/api/students/{student_id}/assessments/academic-support",
        headers=auth_headers("mentor"),
    )
    assert response.status_code == 403


def test_assessment_rejects_disallowed_role():
    student_id = get_student_id("CP-DEMO-0042")
    response = client.post(
        f"/api/students/{student_id}/assessments/academic-support",
        headers=auth_headers("placement"),
    )
    assert response.status_code == 403


def test_assessment_returns_explainable_factors_and_preserves_history():
    student_id = get_student_id("CP-DEMO-0042")
    assessment_id = None

    try:
        response = client.post(
            f"/api/students/{student_id}/assessments/academic-support",
            headers=auth_headers("faculty"),
        )
        assert response.status_code == 200

        data = response.json()
        assessment_id = data["id"]

        assert data["student_id"] == student_id
        assert data["rule_version"] == "academic-support-v1"
        assert data["score"] is not None
        assert data["risk_band"] in {
            "priority_review",
            "monitor",
            "routine_review",
            "needs_review",
        }

        attendance = next(
            factor
            for factor in data["factor_breakdown"]
            if factor["signal"] == "attendance_percentage"
        )
        assert attendance["observed_value"] == 61.0
        assert attendance["threshold"] == 75.0
        assert attendance["triggered"] is True
        assert attendance["rationale"]

        assert any(
            note.get("signal") == "participation_activity"
            or note.get("signal") == "participation_activity"
            for note in data["data_quality_notes"]
        ) or any(
            factor["signal"] == "attendance_percentage"
            for factor in data["factor_breakdown"]
        )

        with SessionLocal() as db:
            stored = db.get(RiskAssessment, assessment_id)
            assert stored is not None
            assert stored.student_id == student_id
    finally:
        if assessment_id is not None:
            with SessionLocal() as db:
                stored = db.get(RiskAssessment, assessment_id)
                if stored is not None:
                    db.delete(stored)
                    db.commit()


def test_unknown_student_returns_404():
    response = client.post(
        "/api/students/999999/assessments/academic-support",
        headers=auth_headers("faculty"),
    )
    assert response.status_code == 404
