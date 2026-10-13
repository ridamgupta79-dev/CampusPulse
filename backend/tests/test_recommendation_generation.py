
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from conftest import auth_headers
from app.models import Recommendation, RiskAssessment, Student

client = TestClient(app)


def get_student_id(code: str) -> int:
    with SessionLocal() as db:
        student = db.scalar(
            select(Student).where(Student.student_code == code)
        )
        assert student is not None
        return student.id


def create_test_assessment(student_id: int) -> int:
    with SessionLocal() as db:
        assessment = RiskAssessment(
            student_id=student_id,
            score=75.0,
            risk_band="priority_review",
            factor_breakdown=[
                {
                    "signal": "attendance_percentage",
                    "observed_value": 55.0,
                    "threshold": 75.0,
                    "triggered": True,
                    "rationale": "Attendance is below the configured threshold.",
                }
            ],
            data_quality_notes=[],
            rule_version="test-rules-v1",
            summary="Temporary assessment for recommendation tests.",
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        return assessment.id


def cleanup_test_records(assessment_id: int) -> None:
    with SessionLocal() as db:
        recommendations = db.scalars(
            select(Recommendation).where(
                Recommendation.assessment_id == assessment_id
            )
        ).all()

        for recommendation in recommendations:
            db.delete(recommendation)

        assessment = db.get(RiskAssessment, assessment_id)
        if assessment is not None:
            db.delete(assessment)

        db.commit()


def test_generation_creates_proposed_recommendation():
    student_id = get_student_id("CP-DEMO-0042")
    assessment_id = create_test_assessment(student_id)

    try:
        response = client.post(
            f"/api/students/{student_id}/assessments/"
            f"{assessment_id}/recommendation",
            headers=auth_headers("faculty"),
        )

        assert response.status_code == 200, response.text
        result = response.json()

        assert result["student_id"] == student_id
        assert result["assessment_id"] == assessment_id
        assert result["status"] == "proposed"
        assert result["created"] is True
        assert "attendance_percentage" in result["contributing_signals"]
        assert "threshold" in result["rationale"]

    finally:
        cleanup_test_records(assessment_id)


def test_generation_is_idempotent_for_same_assessment():
    student_id = get_student_id("CP-DEMO-0042")
    assessment_id = create_test_assessment(student_id)

    try:
        url = (
            f"/api/students/{student_id}/assessments/"
            f"{assessment_id}/recommendation"
        )
        headers=auth_headers("faculty")

        first = client.post(url, headers=headers)
        second = client.post(url, headers=headers)

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text

        first_result = first.json()
        second_result = second.json()

        assert first_result["created"] is True
        assert second_result["created"] is False
        assert first_result["id"] == second_result["id"]

        with SessionLocal() as db:
            records = db.scalars(
                select(Recommendation).where(
                    Recommendation.assessment_id == assessment_id
                )
            ).all()
            assert len(records) == 1

    finally:
        cleanup_test_records(assessment_id)


def test_generation_requires_allowed_role():
    student_id = get_student_id("CP-DEMO-0042")
    assessment_id = create_test_assessment(student_id)

    try:
        response = client.post(
            f"/api/students/{student_id}/assessments/"
            f"{assessment_id}/recommendation",
            headers=auth_headers("placement"),
        )

        assert response.status_code == 403

    finally:
        cleanup_test_records(assessment_id)


def test_generation_rejects_assessment_without_triggered_factors():
    student_id = get_student_id("CP-DEMO-0042")

    with SessionLocal() as db:
        assessment = RiskAssessment(
            student_id=student_id,
            score=0.0,
            risk_band="routine_review",
            factor_breakdown=[
                {
                    "signal": "attendance_percentage",
                    "observed_value": 90.0,
                    "threshold": 75.0,
                    "triggered": False,
                    "rationale": "Attendance is above the configured threshold.",
                }
            ],
            data_quality_notes=[],
            rule_version="test-rules-v1",
            summary="Temporary assessment without triggered factors.",
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        assessment_id = assessment.id

    try:
        response = client.post(
            f"/api/students/{student_id}/assessments/"
            f"{assessment_id}/recommendation",
            headers=auth_headers("faculty"),
        )

        assert response.status_code == 422

    finally:
        cleanup_test_records(assessment_id)


def test_generation_does_not_modify_seeded_recommendation():
    with SessionLocal() as db:
        seeded = db.get(Recommendation, 1)
        assert seeded is not None

        original_status = seeded.status
        original_reason = seeded.rationale
        original_assessment_id = seeded.assessment_id

    student_id = get_student_id("CP-DEMO-0042")
    assessment_id = create_test_assessment(student_id)

    try:
        response = client.post(
            f"/api/students/{student_id}/assessments/"
            f"{assessment_id}/recommendation",
            headers=auth_headers("faculty"),
        )

        assert response.status_code == 200, response.text

        with SessionLocal() as db:
            seeded_after = db.get(Recommendation, 1)
            assert seeded_after is not None
            assert seeded_after.status == original_status
            assert seeded_after.rationale == original_reason
            assert seeded_after.assessment_id == original_assessment_id

    finally:
        cleanup_test_records(assessment_id)
