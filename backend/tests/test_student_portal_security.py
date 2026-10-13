"""Authentication, privacy, and enrollment security for the student portal."""
from sqlalchemy import select

from conftest import auth_headers, client
from portal_helpers import (
    create_student_record,
    get_student_by_code,
    get_user_by_email,
    link_account_directly,
    login_headers,
    register_account,
)

from app.db.session import SessionLocal
from app.models import StudentAccountLink
from app.models.student_enrollment_code import StudentEnrollmentCode


STUDENT_EMAIL = "portal.security.student@example.com"
STUDENT_CODE = "CP-TEST-SEC-1"


def issue_code(student_code: str) -> str:
    response = client.post(
        "/api/staff/enrollment-codes",
        json={"student_code": student_code},
        headers=auth_headers("faculty"),
    )
    assert response.status_code == 200, response.text
    return response.json()["enrollment_code"]


def test_student_registration_and_enrollment_flow():
    create_student_record(STUDENT_CODE, "Security Flow Student", "IT-Year-2")
    register_account(client, STUDENT_EMAIL)

    headers = login_headers(client, STUDENT_EMAIL, "student")

    # Unlinked student accounts cannot read portal data.
    me = client.get("/api/student/me", headers=headers)
    assert me.status_code == 403
    assert "enrollment" in me.json()["detail"].lower()

    # Knowing the student code alone is not enough: wrong code rejected.
    code = issue_code(STUDENT_CODE)
    wrong = client.post(
        "/api/student/enroll",
        json={"student_code": STUDENT_CODE, "enrollment_code": "CP-WRONG99"},
        headers=headers,
    )
    assert wrong.status_code == 400

    # Code mismatch between code and student code is rejected.
    other_code = issue_code("CP-DEMO-0043")
    mismatch = client.post(
        "/api/student/enroll",
        json={"student_code": STUDENT_CODE, "enrollment_code": other_code},
        headers=headers,
    )
    assert mismatch.status_code == 400

    valid = client.post(
        "/api/student/enroll",
        json={"student_code": STUDENT_CODE, "enrollment_code": code},
        headers=headers,
    )
    assert valid.status_code == 200, valid.text
    assert valid.json()["student"]["student_code"] == STUDENT_CODE

    # The same code cannot be redeemed again by anyone.
    second_account = "portal.security.second@example.com"
    register_account(client, second_account)
    second_headers = login_headers(client, second_account, "student")
    replay = client.post(
        "/api/student/enroll",
        json={"student_code": STUDENT_CODE, "enrollment_code": code},
        headers=second_headers,
    )
    assert replay.status_code == 400

    # One record cannot be claimed by two accounts.
    second_code = issue_code(STUDENT_CODE)
    claim = client.post(
        "/api/student/enroll",
        json={"student_code": STUDENT_CODE, "enrollment_code": second_code},
        headers=second_headers,
    )
    assert claim.status_code == 409

    # After enrollment the student sees exactly their own record.
    me = client.get("/api/student/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["student"]["student_code"] == STUDENT_CODE


def test_student_cannot_access_staff_apis():
    create_student_record("CP-TEST-SEC-2", "Staff Guard Student", "IT-Year-2")
    email = "portal.staffguard@example.com"
    register_account(client, email)
    headers = login_headers(client, email, "student")

    assert (
        client.get("/api/students", headers=headers).status_code == 403
    )
    assert (
        client.get("/api/analytics/cohort", headers=headers).status_code == 403
    )
    assert (
        client.get("/api/recommendations", headers=headers).status_code == 403
    )
    assert (
        client.get("/api/interventions", headers=headers).status_code == 403
    )
    assert (
        client.post(
            "/api/students/1/assessments/academic-support",
            headers=headers,
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/students/1/360", headers=headers
        ).status_code
        == 403
    )


def test_demo_role_header_grants_nothing():
    email = "portal.header@example.com"
    create_student_record("CP-TEST-SEC-3", "Header Guard Student", "IT-Year-2")
    register_account(client, email)
    headers = login_headers(client, email, "student")
    spoofed = {**headers, "X-Demo-Role": "hod"}

    assert client.get("/api/analytics/cohort", headers=spoofed).status_code == 403
    assert client.get("/api/students", headers=spoofed).status_code == 403

    unauthenticated = {"X-Demo-Role": "hod"}
    response = client.get("/api/analytics/cohort", headers=unauthenticated)
    assert response.status_code == 401


def test_student_cannot_use_teacher_or_staff_actions():
    email = "portal.actions@example.com"
    create_student_record("CP-TEST-SEC-4", "Action Guard Student", "IT-Year-2")
    register_account(client, email)
    link_account_directly(email, "CP-TEST-SEC-4")
    headers = login_headers(client, email, "student")

    assert (
        client.post(
            "/api/teacher/assignments",
            json={},
            headers=headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/staff/enrollment-codes",
            json={"student_code": "CP-TEST-SEC-4"},
            headers=headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/teacher/submissions/1/grade",
            json={
                "marks_obtained": 10,
                "quality_points": 3,
                "feedback": "self-graded",
                "release": True,
            },
            headers=headers,
        ).status_code
        == 403
    )


def test_student_cannot_impersonate_or_read_other_records():
    create_student_record("CP-TEST-SEC-5", "Student Five", "IT-Year-2")
    create_student_record("CP-TEST-SEC-6", "Student Six", "IT-Year-2")

    email_five = "portal.five@example.com"
    register_account(client, email_five)
    link_account_directly(email_five, "CP-TEST-SEC-5")
    headers_five = login_headers(client, email_five, "student")

    me = client.get("/api/student/me", headers=headers_five)
    assert me.status_code == 200
    own_id = me.json()["student"]["id"]

    other = get_student_by_code("CP-TEST-SEC-6")

    # There is no endpoint that accepts an arbitrary student id on the
    # student portal; verify the profile and academics are always the
    # linked record, never a requested one.
    profile = client.get("/api/student/profile", headers=headers_five)
    assert profile.status_code == 200
    assert profile.json()["student"]["id"] == own_id

    academics = client.get("/api/student/academics", headers=headers_five)
    assert academics.status_code == 200
    assert academics.json()["student"]["student_code"] == "CP-TEST-SEC-5"
    assert other.student_code not in academics.text


def test_account_link_cannot_be_hijacked():
    # A second user cannot re-point an existing link.
    create_student_record("CP-TEST-SEC-7", "Student Seven", "IT-Year-2")
    email = "portal.hijack@example.com"
    register_account(client, email)
    link_account_directly(email, "CP-TEST-SEC-7")

    email_attacker = "portal.hijack.attacker@example.com"
    register_account(client, email_attacker)
    attacker_headers = login_headers(client, email_attacker, "student")

    code = issue_code("CP-TEST-SEC-7")
    response = client.post(
        "/api/student/enroll",
        json={"student_code": "CP-TEST-SEC-7", "enrollment_code": code},
        headers=attacker_headers,
    )
    assert response.status_code == 409

    with SessionLocal() as db:
        attacker = get_user_by_email(email_attacker)
        links = list(
            db.scalars(
                select(StudentAccountLink).where(
                    StudentAccountLink.user_id == attacker.id
                )
            )
        )
        assert links == []
