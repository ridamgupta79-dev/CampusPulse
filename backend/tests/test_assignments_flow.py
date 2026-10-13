"""Assignment lifecycle: publication, submission, deadlines, and grading."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from conftest import client
from portal_helpers import (
    create_student_record,
    link_account_directly,
    login_headers,
    register_account,
)

from app.db.session import SessionLocal
from app.models import Assignment, AssignmentSubmission

TEACHER_EMAIL = "assignments.teacher@example.com"
TEACHER_HEADERS = None

COHORT = "IT-Year-2"
STUDENT_A = "CP-TEST-ASG-A"
STUDENT_B = "CP-TEST-ASG-B"
STUDENT_A_EMAIL = "assignments.studenta@example.com"
STUDENT_B_EMAIL = "assignments.studentb@example.com"


def setup_module(module):
    global TEACHER_HEADERS
    response = client.post(
        "/api/auth/login",
        json={
            "email": TEACHER_EMAIL,
            "password": "PortalTeacher@123",
            "role": "faculty",
        },
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
    else:
        # Provision the teacher directly (trusted process, as in production).
        from sqlalchemy import select as _select

        from app.api.routes.auth import _hash_password
        from app.db.session import SessionLocal as _SL
        from app.models.auth_user import AuthUser as _AuthUser

        with _SL() as db:
            user = db.scalar(
                _select(_AuthUser).where(_AuthUser.email == TEACHER_EMAIL)
            )
            if user is None:
                user = _AuthUser(
                    email=TEACHER_EMAIL,
                    full_name="Assignments Test Teacher",
                    role="faculty",
                    password_hash=_hash_password("PortalTeacher@123"),
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
        response = client.post(
            "/api/auth/login",
            json={
                "email": TEACHER_EMAIL,
                "password": "PortalTeacher@123",
                "role": "faculty",
            },
        )
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
    TEACHER_HEADERS = {"Authorization": f"Bearer {token}"}

    create_student_record(STUDENT_A, "Assignment Student A", COHORT)
    create_student_record(STUDENT_B, "Assignment Student B", COHORT)
    register_account(client, STUDENT_A_EMAIL)
    register_account(client, STUDENT_B_EMAIL)
    link_account_directly(STUDENT_A_EMAIL, STUDENT_A)
    link_account_directly(STUDENT_B_EMAIL, STUDENT_B)


def student_headers(email: str) -> dict:
    return login_headers(client, email, "student")


def _create_assignment(**overrides) -> dict:
    now = datetime.now(timezone.utc)
    payload = {
        "title": overrides.pop("title", "Integration Worksheet"),
        "description": "Test assignment description.",
        "instructions": "Answer in text.",
        "subject": "Software Testing",
        "cohort": overrides.pop("cohort", COHORT),
        "due_at": overrides.pop(
            "due_at", (now + timedelta(days=3)).isoformat()
        ),
        "max_marks": overrides.pop("max_marks", 20),
        "allow_late_submissions": overrides.pop("allow_late_submissions", True),
        "late_window_hours": overrides.pop("late_window_hours", 24),
        "publish_now": overrides.pop("publish_now", True),
    }
    response = client.post(
        "/api/teacher/assignments",
        json=payload,
        headers=TEACHER_HEADERS,
    )
    assert response.status_code == 201, response.text
    return response.json()["assignment"]


def test_teacher_creates_and_students_see_assignment():
    assignment = _create_assignment(title="Visibility Check Worksheet")
    assert assignment["status"] == "published"

    response = client.get(
        "/api/student/assignments", headers=student_headers(STUDENT_A_EMAIL)
    )
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()]
    assert "Visibility Check Worksheet" in titles

    # A student from another cohort must not see it.
    create_student_record("CP-TEST-ASG-C", "Other Cohort Student", "CS-Year-1")
    other_email = "assignments.studentc@example.com"
    register_account(client, other_email)
    link_account_directly(other_email, "CP-TEST-ASG-C")
    response = client.get(
        "/api/student/assignments", headers=student_headers(other_email)
    )
    assert response.status_code == 200
    assert "Visibility Check Worksheet" not in [
        item["title"] for item in response.json()
    ]


def test_valid_submission_and_resubmission_flow():
    assignment = _create_assignment(title="Submission Flow Worksheet")
    headers = student_headers(STUDENT_A_EMAIL)

    draft = client.post(
        f"/api/student/assignments/{assignment['id']}/submit",
        json={"text_answer": "Draft answer", "as_draft": True},
        headers=headers,
    )
    assert draft.status_code == 200
    assert draft.json()["submission"]["status"] == "draft"

    submitted = client.post(
        f"/api/student/assignments/{assignment['id']}/submit",
        json={"text_answer": "My final answer for the worksheet."},
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    body = submitted.json()["submission"]
    assert body["status"] == "submitted"
    assert body["is_late"] is False
    assert body["submitted_at"].endswith("+00:00")
    assert body["timing_points"] == 4

    # Grading locks the submission.
    grade = client.post(
        f"/api/teacher/submissions/{body['id']}/grade",
        json={
            "marks_obtained": 18,
            "quality_points": 3,
            "feedback": "Nice work.",
            "release": True,
        },
        headers=TEACHER_HEADERS,
    )
    assert grade.status_code == 200, grade.text
    assert grade.json()["points_awarded"] == 7

    blocked = client.post(
        f"/api/student/assignments/{assignment['id']}/submit",
        json={"text_answer": "Trying to change a graded submission."},
        headers=headers,
    )
    assert blocked.status_code == 409


def test_deadline_classification_is_server_side():
    now = datetime.now(timezone.utc)

    late_allowed = _create_assignment(
        title="Late Window Worksheet",
        due_at=(now - timedelta(hours=2)).isoformat(),
        allow_late_submissions=True,
        late_window_hours=24,
    )
    response = client.post(
        f"/api/student/assignments/{late_allowed['id']}/submit",
        json={"text_answer": "Late but inside the window."},
        headers=student_headers(STUDENT_A_EMAIL),
    )
    assert response.status_code == 200
    assert response.json()["submission"]["is_late"] is True
    assert response.json()["submission"]["timing_points"] == 1

    no_late = _create_assignment(
        title="No Late Worksheet",
        due_at=(now - timedelta(hours=1)).isoformat(),
        allow_late_submissions=False,
    )
    response = client.post(
        f"/api/student/assignments/{no_late['id']}/submit",
        json={"text_answer": "Past deadline, not allowed."},
        headers=student_headers(STUDENT_A_EMAIL),
    )
    assert response.status_code == 409

    beyond_window = _create_assignment(
        title="Beyond Window Worksheet",
        due_at=(now - timedelta(hours=30)).isoformat(),
        allow_late_submissions=True,
        late_window_hours=24,
    )
    response = client.post(
        f"/api/student/assignments/{beyond_window['id']}/submit",
        json={"text_answer": "Way too late."},
        headers=student_headers(STUDENT_A_EMAIL),
    )
    assert response.status_code == 409


def test_closed_assignment_rejects_submissions():
    assignment = _create_assignment(title="Close Check Worksheet")
    close = client.post(
        f"/api/teacher/assignments/{assignment['id']}/close",
        headers=TEACHER_HEADERS,
    )
    assert close.status_code == 200

    response = client.post(
        f"/api/student/assignments/{assignment['id']}/submit",
        json={"text_answer": "Should not be accepted."},
        headers=student_headers(STUDENT_A_EMAIL),
    )
    assert response.status_code == 409


def test_feedback_hidden_until_release_and_visible_after():
    assignment = _create_assignment(title="Feedback Gate Worksheet")
    headers = student_headers(STUDENT_B_EMAIL)

    submitted = client.post(
        f"/api/student/assignments/{assignment['id']}/submit",
        json={"text_answer": "Answer for feedback gating."},
        headers=headers,
    )
    submission_id = submitted.json()["submission"]["id"]

    saved = client.post(
        f"/api/teacher/submissions/{submission_id}/grade",
        json={
            "marks_obtained": 15,
            "quality_points": 2,
            "feedback": "Secret feedback before release.",
            "release": False,
        },
        headers=TEACHER_HEADERS,
    )
    assert saved.status_code == 200
    assert saved.json()["status"] == "returned"

    listing = client.get(
        "/api/student/assignments?filter=all", headers=headers
    )
    item = next(
        i
        for i in listing.json()
        if i["id"] == assignment["id"]
    )
    assert item["submission"]["feedback"] is None
    assert item["submission"]["feedback_released"] is False

    # A returned submission can be revised.
    revised = client.post(
        f"/api/student/assignments/{assignment['id']}/submit",
        json={"text_answer": "Improved answer after revision."},
        headers=headers,
    )
    assert revised.status_code == 200

    released = client.post(
        f"/api/teacher/submissions/{submission_id}/grade",
        json={
            "marks_obtained": 17,
            "quality_points": 2,
            "feedback": "Released feedback text.",
            "release": True,
        },
        headers=TEACHER_HEADERS,
    )
    assert released.status_code == 200

    detail = client.get(
        f"/api/student/assignments/{assignment['id']}", headers=headers
    )
    assert detail.json()["submission"]["feedback"] == "Released feedback text."
    assert detail.json()["submission"]["feedback_released"] is True


def test_teacher_scope_is_object_level():
    assignment = _create_assignment(title="Scope Check Worksheet")
    headers = student_headers(STUDENT_A_EMAIL)
    submitted = client.post(
        f"/api/student/assignments/{assignment['id']}/submit",
        json={"text_answer": "Scope test answer."},
        headers=headers,
    )
    submission_id = submitted.json()["submission"]["id"]

    # A second teacher cannot grade or even list these submissions.
    from sqlalchemy import select as _select

    from app.api.routes.auth import _hash_password
    from app.db.session import SessionLocal as _SL
    from app.models.auth_user import AuthUser as _AuthUser

    other_teacher_email = "assignments.teacher2@example.com"
    with _SL() as db:
        user = db.scalar(
            _select(_AuthUser).where(_AuthUser.email == other_teacher_email)
        )
        if user is None:
            db.add(_AuthUser(
                email=other_teacher_email,
                full_name="Other Teacher",
                role="faculty",
                password_hash=_hash_password("PortalTeacher@123"),
                is_active=True,
            ))
            db.commit()
    other_login = client.post(
        "/api/auth/login",
        json={
            "email": other_teacher_email,
            "password": "PortalTeacher@123",
            "role": "faculty",
        },
    )
    other_headers = {
        "Authorization": f"Bearer {other_login.json()['access_token']}"
    }

    assert (
        client.get(
            f"/api/teacher/assignments/{assignment['id']}/submissions",
            headers=other_headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/teacher/submissions/{submission_id}/grade",
            json={
                "marks_obtained": 20,
                "quality_points": 3,
                "feedback": "not mine",
                "release": True,
            },
            headers=other_headers,
        ).status_code
        == 403
    )


def test_student_home_and_academics_use_backend_data():
    headers = student_headers(STUDENT_A_EMAIL)
    home = client.get("/api/student/home", headers=headers)
    assert home.status_code == 200
    body = home.json()
    assert body["student"]["student_code"] == STUDENT_A
    assert "pulse_balance" in body and "upcoming_deadlines" in body

    academics = client.get("/api/student/academics", headers=headers)
    assert academics.status_code == 200
    assert academics.json()["student"]["student_code"] == STUDENT_A
