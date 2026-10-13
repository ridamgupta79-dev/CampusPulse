
from fastapi.testclient import TestClient

from app.main import app
from conftest import auth_headers

client = TestClient(app)


def test_cohort_analytics_requires_authentication():
    response = client.get("/api/analytics/cohort")
    assert response.status_code == 401


def test_cohort_analytics_denies_faculty_role():
    response = client.get(
        "/api/analytics/cohort",
        headers=auth_headers("faculty"),
    )
    assert response.status_code == 403


def test_cohort_analytics_allows_hod_role():
    response = client.get(
        "/api/analytics/cohort",
        headers=auth_headers("hod"),
    )

    assert response.status_code == 200, response.text
    result = response.json()

    assert "student_count" in result
    assert "risk_distribution" in result
    assert "intervention_workload" in result
    assert "outcome_coverage" in result
    assert "data_quality" in result


def test_cohort_analytics_supports_cohort_filter():
    response = client.get(
        "/api/analytics/cohort",
        headers=auth_headers("hod"),
        params={"cohort": "Cohort That Does Not Exist"},
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["student_count"] == 0
    assert result["risk_distribution"] == {}


def test_cohort_analytics_rejects_invalid_stale_window():
    response = client.get(
        "/api/analytics/cohort",
        headers=auth_headers("hod"),
        params={"stale_after_days": 0},
    )

    assert response.status_code == 422


def test_cohort_analytics_does_not_expose_student_identifiers():
    response = client.get(
        "/api/analytics/cohort",
        headers=auth_headers("hod"),
    )

    assert response.status_code == 200
    result = response.json()

    assert "students" not in result
    assert "student_code" not in result
    assert "full_name" not in result
