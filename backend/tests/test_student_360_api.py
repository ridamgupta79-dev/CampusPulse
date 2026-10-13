
from fastapi.testclient import TestClient

from app.main import app
from conftest import auth_headers
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.student_consent import StudentConsent

client = TestClient(app)


def get_demo_student_id() -> int:
    response = client.get("/api/students", headers=auth_headers("hod"))
    assert response.status_code == 200

    students = response.json()
    student = next(
        item
        for item in students
        if item["student_code"] == "CP-DEMO-0042"
    )
    return student["id"]


def test_student_360_requires_authentication():
    student_id = get_demo_student_id()

    response = client.get(f"/api/students/{student_id}/360")

    assert response.status_code == 401


def test_faculty_receives_only_permitted_consented_signals():
    student_id = get_demo_student_id()

    response = client.get(
        f"/api/students/{student_id}/360",
        headers=auth_headers("faculty"),
    )

    assert response.status_code == 200

    data = response.json()
    assert data["viewer_role"] == "faculty"
    assert data["student"]["student_code"] == "CP-DEMO-0042"

    domains = {signal["domain"] for signal in data["signals"]}

    assert "fees" not in domains
    assert "skills" not in domains

    for signal in data["signals"]:
        assert signal["domain"] in {
            "attendance",
            "academics",
            "participation",
            "faculty_feedback",
        }


def test_placement_cannot_access_signals_without_granted_consent():
    student_id = get_demo_student_id()

    response = client.get(
        f"/api/students/{student_id}/360",
        headers=auth_headers("placement"),
    )

    assert response.status_code == 200

    data = response.json()

    # This demo student has declined placement support.
    assert all(
        signal["domain"] not in {"skills"}
        for signal in data["signals"]
    )


def test_nonexistent_student_returns_404():
    response = client.get(
        "/api/students/999999/360",
        headers=auth_headers("faculty"),
    )

    assert response.status_code == 404


def test_withdrawn_consent_hides_academic_signals():
    student_id = get_demo_student_id()

    with SessionLocal() as db:
        consent = db.scalar(
            select(StudentConsent).where(
                StudentConsent.student_id == student_id,
                StudentConsent.purpose == "academic_support",
            )
        )

        assert consent is not None

        original_status = consent.status

        try:
            consent.status = "withdrawn"
            db.commit()

            response = client.get(
                f"/api/students/{student_id}/360",
                headers=auth_headers("faculty"),
            )

            assert response.status_code == 200

            data = response.json()

            academic_domains = {
                "attendance",
                "academics",
                "participation",
                "faculty_feedback",
            }

            assert all(
                signal["domain"] not in academic_domains
                for signal in data["signals"]
            )

        finally:
            consent.status = original_status
            db.commit()


def test_missing_or_stale_signals_keep_their_quality_status():
    student_id = get_demo_student_id()

    response = client.get(
        f"/api/students/{student_id}/360",
        headers=auth_headers("faculty"),
    )

    assert response.status_code == 200

    signals = response.json()["signals"]

    # Missing and stale records must retain their recorded quality.
    # They must not be silently converted into zero-valued evidence.
    quality_labels = {
        signal["quality_status"].strip().lower()
        for signal in signals
    }

    assert "missing" in quality_labels

    for signal in signals:
        if signal["quality_status"].strip().lower() in {
            "missing",
            "stale",
        }:
            assert signal["numeric_value"] is None

