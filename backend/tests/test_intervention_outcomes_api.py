
from fastapi.testclient import TestClient

from app.main import app
from conftest import auth_headers

client = TestClient(app)


def test_outcome_endpoint_requires_authentication():
    response = client.post(
        "/api/interventions/1/outcomes",
        json={"metric_name": "Assessment average"},
    )
    assert response.status_code == 401


def test_outcome_endpoint_returns_404_for_unknown_intervention():
    response = client.post(
        "/api/interventions/999999/outcomes",
        headers=auth_headers("hod"),
        json={"metric_name": "Assessment average"},
    )
    assert response.status_code == 404


def test_outcome_endpoint_rejects_invalid_classification():
    response = client.post(
        "/api/interventions/1/outcomes",
        headers=auth_headers("faculty"),
        json={
            "metric_name": "Assessment average",
            "classification": "guaranteed_success",
        },
    )
    assert response.status_code == 422


def test_outcome_endpoint_rejects_incomplete_measurement_dates():
    response = client.post(
        "/api/interventions/1/outcomes",
        headers=auth_headers("faculty"),
        json={
            "metric_name": "Assessment average",
            "baseline_value": 52,
        },
    )
    assert response.status_code == 422


def test_outcome_endpoint_rejects_unknown_evidence_quality():
    response = client.post(
        "/api/interventions/1/outcomes",
        headers=auth_headers("faculty"),
        json={
            "metric_name": "Assessment average",
            "evidence_quality": "perfect",
        },
    )
    assert response.status_code == 422
