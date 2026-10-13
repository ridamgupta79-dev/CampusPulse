"""Security tests for real authentication and backend authorization.

Covers registration, login, token validation, role enforcement, consent
checks, IDOR resistance, and preservation of the existing database records.
All requests run against the isolated test database prepared by conftest.
"""
from datetime import timedelta

from sqlalchemy import select

from conftest import auth_headers, client
from app.core.security import create_access_token
from app.db.init_db import create_tables
from app.db.session import SessionLocal
from app.models import Student, StudentSignal
from app.models.auth_user import AuthUser


def get_student_id(code: str) -> int:
    with SessionLocal() as db:
        student = db.scalar(
            select(Student).where(Student.student_code == code)
        )
        assert student is not None
        return student.id


def get_user_id(email: str) -> int:
    with SessionLocal() as db:
        user = db.scalar(select(AuthUser).where(AuthUser.email == email))
        assert user is not None
        return user.id


def register(email: str, role: str = "mentor"):
    return client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "SecurePass123",
            "full_name": "Security Test User",
            "role": role,
        },
    )


# 1. Valid registration succeeds.
def test_valid_registration_succeeds():
    response = register("security.register@example.com")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["role"] == "mentor"
    assert body["access_token"]

    with SessionLocal() as db:
        stored = db.scalar(
            select(AuthUser).where(
                AuthUser.email == "security.register@example.com"
            )
        )
        assert stored is not None
        assert stored.role == "mentor"
        assert "pbkdf2_sha256" in stored.password_hash


# 2. Duplicate registration is rejected.
def test_duplicate_registration_is_rejected():
    first = register("security.duplicate@example.com")
    assert first.status_code == 201

    second = register("security.duplicate@example.com")
    assert second.status_code == 409


# Extra policy checks for open registration safety.
def test_self_registration_cannot_create_privileged_roles():
    for role in ("hod", "faculty", "counsellor", "finance", "placement"):
        response = register(f"security.priv-{role}@example.com", role=role)
        assert response.status_code == 403, (role, response.text)
        assert "Self-registration" in response.json()["detail"]


# 3. Correct credentials permit login.
def test_correct_credentials_permit_login():
    response = client.post(
        "/api/auth/login",
        json={
            "email": "faculty@campuspulse.demo",
            "password": "CampusPulse@123",
            "role": "faculty",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["role"] == "faculty"


# 4. Incorrect credentials are rejected.
def test_incorrect_credentials_are_rejected():
    response = client.post(
        "/api/auth/login",
        json={
            "email": "faculty@campuspulse.demo",
            "password": "WrongPassword999",
            "role": "faculty",
        },
    )
    assert response.status_code == 401


# 5. A mismatched role is rejected according to the existing account policy.
def test_login_with_mismatched_role_is_rejected():
    response = client.post(
        "/api/auth/login",
        json={
            "email": "hod@campuspulse.demo",
            "password": "CampusPulse@123",
            "role": "faculty",
        },
    )
    assert response.status_code == 403


# 6. Unauthenticated access to protected APIs is rejected.
def test_unauthenticated_access_is_rejected():
    endpoints = [
        ("get", "/api/students"),
        ("get", "/api/students/1"),
        ("get", "/api/students/1/360"),
        ("get", "/api/recommendations"),
        ("get", "/api/interventions"),
        ("get", "/api/analytics/cohort"),
        ("post", "/api/students/1/assessments/academic-support"),
        ("post", "/api/recommendations/1/review"),
        ("patch", "/api/interventions/1/status"),
        ("post", "/api/interventions/1/follow-up"),
        ("post", "/api/interventions/1/outcomes"),
    ]

    for method, path in endpoints:
        call = getattr(client, method)
        if method == "get":
            response = call(path)
        else:
            response = call(path, json={})
        assert response.status_code == 401, (method, path, response.status_code)


# 7. An authenticated user can access a permitted endpoint.
def test_authenticated_user_accesses_permitted_endpoint():
    response = client.get("/api/students", headers=auth_headers("mentor"))
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


# 8. A user cannot access a restricted endpoint by changing X-Demo-Role.
def test_header_role_cannot_grant_hod_privileges():
    mentor = auth_headers("mentor")

    response = client.get(
        "/api/analytics/cohort",
        headers={**mentor, "X-Demo-Role": "hod"},
    )
    assert response.status_code == 403

    plain_header = client.get(
        "/api/analytics/cohort",
        headers={"X-Demo-Role": "hod"},
    )
    assert plain_header.status_code == 401


# 9. A user cannot gain HOD privileges by modifying request payloads.
def test_payload_role_claims_cannot_escalate_privileges():
    faculty_id = get_user_id("faculty@campuspulse.demo")

    # Token signed with the real secret but carrying a forged role claim:
    # authorization must still come from the persisted account.
    forged = create_access_token(faculty_id, role="hod")

    response = client.get(
        "/api/analytics/cohort",
        headers={
            "Authorization": f"Bearer {forged}",
            "X-Demo-Role": "hod",
        },
    )
    assert response.status_code == 403

    payload = client.get(
        "/api/analytics/cohort",
        headers={"Authorization": f"Bearer {forged}"},
        params={"role": "hod"},
    )
    assert payload.status_code == 403


# 10. A user cannot access another student's restricted information by ID.
def test_student_id_changes_cannot_bypass_domain_permissions():
    # Neither CP-DEMO-0042 nor CP-DEMO-0043 recorded finance_support
    # consent, so a finance account must see no signals for either student,
    # whichever id it requests.
    student_ids = [
        get_student_id("CP-DEMO-0042"),
        get_student_id("CP-DEMO-0043"),
    ]

    for student_id in student_ids:
        response = client.get(
            f"/api/students/{student_id}/360",
            headers=auth_headers("finance"),
        )
        assert response.status_code == 200
        body = response.json()
        domains = {signal["domain"] for signal in body["signals"]}
        assert domains == set(), domains


# 11. Consent restrictions remain enforced.
def test_consent_restrictions_remain_enforced():
    # CP-DEMO-0042 granted academic_support; faculty may see those domains.
    student_42 = get_student_id("CP-DEMO-0042")
    response = client.get(
        f"/api/students/{student_42}/360",
        headers=auth_headers("faculty"),
    )
    assert response.status_code == 200
    domains = {signal["domain"] for signal in response.json()["signals"]}
    assert domains <= {"attendance", "academics", "participation", "faculty_feedback"}

    # The same student declined placement_support, so the skills domain is
    # hidden from placement even though the role normally permits it.
    # Academics stays visible because academic_support was granted.
    response = client.get(
        f"/api/students/{student_42}/360",
        headers=auth_headers("placement"),
    )
    assert response.status_code == 200
    domains = {signal["domain"] for signal in response.json()["signals"]}
    assert domains == {"academics"}
    assert "skills" not in domains

    # Counsellors have no visible signal domains at all.
    response = client.get(
        f"/api/students/{student_42}/360",
        headers=auth_headers("counsellor"),
    )
    assert response.status_code == 200
    assert response.json()["signals"] == []


# 12. HOD-only analytics cannot be accessed by unauthorized roles.
def test_hod_only_analytics_rejects_other_roles():
    for role in ("faculty", "mentor", "counsellor", "finance", "placement"):
        response = client.get(
            "/api/analytics/cohort",
            headers=auth_headers(role),
        )
        assert response.status_code == 403, role

    hod = client.get("/api/analytics/cohort", headers=auth_headers("hod"))
    assert hod.status_code == 200


# 13. Expired or invalid tokens are rejected.
def test_expired_and_invalid_tokens_are_rejected():
    faculty_id = get_user_id("faculty@campuspulse.demo")
    expired = create_access_token(
        faculty_id,
        role="faculty",
        expires_delta=timedelta(seconds=-30),
    )

    response = client.get(
        "/api/students",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert response.status_code == 401

    for bad in ("not-a-token", "a.b.c", ""):
        response = client.get(
            "/api/students",
            headers={"Authorization": f"Bearer {bad}"},
        )
        assert response.status_code == 401

    # A token for a user id that does not exist must also be rejected.
    ghost = create_access_token(999999999, role="hod")
    response = client.get(
        "/api/students",
        headers={"Authorization": f"Bearer {ghost}"},
    )
    assert response.status_code == 401

    # Wrong scheme is rejected.
    response = client.get(
        "/api/students",
        headers={"Authorization": "Basic Zm9vOmJhcg=="},
    )
    assert response.status_code == 401


# 14. Intervention status updates and follow-up still work when authorized.
def test_authorized_intervention_operations_still_work():
    from datetime import datetime, timedelta, timezone

    from app.models.intervention import Intervention
    from app.models.intervention_event import InterventionEvent

    student_42 = get_student_id("CP-DEMO-0042")
    headers = auth_headers("faculty")
    intervention_id = None

    try:
        with SessionLocal() as db:
            intervention = Intervention(
                student_id=student_42,
                recommendation_id=None,
                intervention_type="security_test_check_in",
                description="Temporary intervention for the security suite",
                assigned_role="faculty",
                assigned_owner="Security Test",
                due_date=datetime.now(timezone.utc) + timedelta(days=7),
                status="assigned",
                priority="medium",
            )
            db.add(intervention)
            db.commit()
            db.refresh(intervention)
            intervention_id = intervention.id

        # Authorized status transition.
        response = client.patch(
            f"/api/interventions/{intervention_id}/status",
            headers=headers,
            json={"status": "in_progress"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "in_progress"

        # Authorized follow-up note.
        response = client.post(
            f"/api/interventions/{intervention_id}/follow-up",
            headers=headers,
            json={"note": "Security-test follow-up; synthetic record."},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "follow_up_recorded"

        # A non-assigned role cannot mutate the same intervention.
        response = client.patch(
            f"/api/interventions/{intervention_id}/status",
            headers=auth_headers("finance"),
            json={"status": "completed"},
        )
        assert response.status_code == 403

    finally:
        if intervention_id is not None:
            with SessionLocal() as db:
                events = db.scalars(
                    select(InterventionEvent).where(
                        InterventionEvent.intervention_id == intervention_id
                    )
                ).all()
                for event in events:
                    db.delete(event)
                record = db.get(Intervention, intervention_id)
                if record is not None:
                    db.delete(record)
                db.commit()


# 15. Existing database records survive initialization.
def test_existing_records_survive_reinitialization():
    with SessionLocal() as db:
        before_students = len(db.scalars(select(Student)).all())
        before_signals = len(db.scalars(select(StudentSignal)).all())
        before_users = len(db.scalars(select(AuthUser)).all())

    # Re-running table initialization must be non-destructive.
    create_tables()

    with SessionLocal() as db:
        assert len(db.scalars(select(Student)).all()) == before_students
        assert len(db.scalars(select(StudentSignal)).all()) == before_signals
        assert len(db.scalars(select(AuthUser)).all()) == before_users

    # Demo accounts keep their persisted roles and password hashes.
    hod = db.scalar(select(AuthUser).where(AuthUser.email == "hod@campuspulse.demo"))
    assert hod is not None and hod.role == "hod"


def test_demo_accounts_are_not_upgraded_or_rewritten():
    with SessionLocal() as db:
        before = {
            user.email: (user.role, user.password_hash)
            for user in db.scalars(select(AuthUser)).all()
        }

    from app.api.routes.auth import seed_demo_users

    with SessionLocal() as db:
        seed_demo_users(db)

    with SessionLocal() as db:
        after = {
            user.email: (user.role, user.password_hash)
            for user in db.scalars(select(AuthUser)).all()
        }

    for email, snapshot in before.items():
        assert after[email] == snapshot
