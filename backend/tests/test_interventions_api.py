
from fastapi.testclient import TestClient

from app.main import app
from conftest import auth_headers

client = TestClient(app)


def test_follow_up_requires_authentication():
    response = client.post(
        "/api/interventions/1/follow-up",
        json={"note": "Follow-up session completed."},
    )
    assert response.status_code == 401


def test_status_update_requires_authentication():
    response = client.patch(
        "/api/interventions/1/status",
        json={"status": "in_progress"},
    )
    assert response.status_code == 401


def test_follow_up_returns_not_found_for_unknown_intervention():
    response = client.post(
        "/api/interventions/999999/follow-up",
        headers=auth_headers("faculty"),
        json={"note": "Follow-up session completed."},
    )
    assert response.status_code == 404


def test_status_update_returns_not_found_for_unknown_intervention():
    response = client.patch(
        "/api/interventions/999999/status",
        headers=auth_headers("faculty"),
        json={"status": "in_progress"},
    )
    assert response.status_code == 404


def test_follow_up_rejects_blank_note():
    response = client.post(
        "/api/interventions/1/follow-up",
        headers=auth_headers("faculty"),
        json={"note": "   "},
    )
    assert response.status_code == 422


def test_status_update_rejects_unknown_status():
    response = client.patch(
        "/api/interventions/1/status",
        headers=auth_headers("faculty"),
        json={"status": "punished"},
    )
    assert response.status_code == 422

def test_list_interventions_requires_authentication():
    response = client.get("/api/interventions")
    assert response.status_code == 401


def test_list_interventions_returns_visible_records():
    response = client.get(
        "/api/interventions",
        headers=auth_headers("faculty"),
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)

    for item in response.json():
        assert "student_name" in item
        assert "student_code" in item
        assert "assigned_owner" in item
        assert "due_date" in item
        assert "status" in item