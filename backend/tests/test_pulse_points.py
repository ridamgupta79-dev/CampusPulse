"""Pulse Points: scoring, idempotent awards, ledger integrity, adjustments."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from conftest import client
from portal_helpers import (
    create_student_record,
    link_account_directly,
    login_headers,
    register_account,
)

from app.db.session import SessionLocal
from app.models import Assignment, AssignmentSubmission, Student
from app.models.auth_user import AuthUser
from app.models.pulse_ledger import PulseLedgerEntry
from app.services.pulse_points import (
    adjust_points,
    compute_timing_points,
    reconcile_account,
)

STUDENT_EMAIL = "pulse.student@example.com"
STUDENT_CODE = "CP-TEST-PULSE-1"
COHORT = "IT-Year-2"


def setup_module(module):
    create_student_record(STUDENT_CODE, "Pulse Student", COHORT)
    register_account(client, STUDENT_EMAIL)
    link_account_directly(STUDENT_EMAIL, STUDENT_CODE)

    with SessionLocal() as db:
        teacher = db.scalar(
            select(AuthUser).where(
                AuthUser.email == "assignments.teacher@example.com"
            )
        )
        if teacher is None:
            from app.api.routes.auth import _hash_password

            db.add(AuthUser(
                email="assignments.teacher@example.com",
                full_name="Assignments Test Teacher",
                role="faculty",
                password_hash=_hash_password("PortalTeacher@123"),
                is_active=True,
            ))
            db.commit()


def student_headers() -> dict:
    return login_headers(client, STUDENT_EMAIL, "student")


def teacher_headers() -> dict:
    response = client.post(
        "/api/auth/login",
        json={
            "email": "assignments.teacher@example.com",
            "password": "PortalTeacher@123",
            "role": "faculty",
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _make_assignment(title: str, *, due_offset, published_offset=None,
                     allow_late=True, late_window_hours=24) -> Assignment:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        teacher = db.scalar(
            select(AuthUser).where(
                AuthUser.email == "assignments.teacher@example.com"
            )
        )
        assert teacher is not None
        assignment = Assignment(
            title=title,
            description="Pulse test assignment.",
            instructions="Text answer.",
            subject="Pulse Testing",
            cohort=COHORT,
            teacher_user_id=teacher.id,
            status="published",
            published_at=published_offset
            and now + published_offset
            or now - timedelta(days=2),
            due_at=now + due_offset,
            max_marks=20,
            allow_late_submissions=allow_late,
            late_window_hours=late_window_hours,
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment


def _submit(assignment_id: int, text: str = "Pulse test answer.") -> dict:
    response = client.post(
        f"/api/student/assignments/{assignment_id}/submit",
        json={"text_answer": text},
        headers=student_headers(),
    )
    assert response.status_code == 200, response.text
    return response.json()["submission"]


def _grade(submission_id: int, quality: int, release=True) -> dict:
    response = client.post(
        f"/api/teacher/submissions/{submission_id}/grade",
        json={
            "marks_obtained": 18,
            "quality_points": quality,
            "feedback": "Graded by test.",
            "release": release,
        },
        headers=teacher_headers(),
    )
    assert response.status_code == 200, response.text
    return response.json()


# ---- pure rubric boundaries (server-side scoring) ----


def test_timing_rubric_boundaries():
    published = datetime(2026, 10, 1, tzinfo=timezone.utc)
    due = published + timedelta(days=10)  # window = 240h

    # >= 20% remaining -> 4
    assert compute_timing_points(
        published, due, due - timedelta(hours=48), True, 24
    ) == 4
    # exactly 20% -> 4
    assert compute_timing_points(
        published, due, due - timedelta(hours=48, seconds=1), True, 24
    ) == 4
    # 10% <= remaining < 20% -> 3
    assert compute_timing_points(
        published, due, due - timedelta(hours=24), True, 24
    ) == 3
    # 0 < remaining < 10% -> 2
    assert compute_timing_points(
        published, due, due - timedelta(hours=12), True, 24
    ) == 2
    # at the deadline -> late branch, within 24h window -> 1
    assert compute_timing_points(
        published, due, due, True, 24
    ) == 1
    # late inside window -> 1
    assert compute_timing_points(
        published, due, due + timedelta(hours=23), True, 24
    ) == 1
    # late beyond window -> 0
    assert compute_timing_points(
        published, due, due + timedelta(hours=25), True, 24
    ) == 0
    # late but late submissions not allowed -> 0
    assert compute_timing_points(
        published, due, due + timedelta(hours=1), False, 24
    ) == 0
    # degenerate zero-length window, on time -> 4
    assert compute_timing_points(
        due, due, due - timedelta(seconds=1), True, 24
    ) == 4


def test_submission_awards_timing_pending_quality_and_final_award():
    assignment = _make_assignment("Pulse Full Flow", due_offset=timedelta(days=3))
    submission = _submit(assignment.id)
    assert submission["timing_points"] == 4
    assert submission["quality_points"] is None

    # Unreviewed work must not have a final award.
    with SessionLocal() as db:
        awards = list(
            db.scalars(
                select(PulseLedgerEntry).where(
                    PulseLedgerEntry.submission_id == submission["id"],
                    PulseLedgerEntry.txn_type == "award",
                )
            )
        )
        assert awards == []

    result = _grade(submission["id"], quality=2)
    assert result["points_awarded"] == 6  # 4 timing + 2 quality
    assert result["status"] == "graded"

    with SessionLocal() as db:
        entries = list(
            db.scalars(
                select(PulseLedgerEntry).where(
                    PulseLedgerEntry.submission_id == submission["id"],
                    PulseLedgerEntry.txn_type == "award",
                )
            )
        )
        assert len(entries) == 1
        assert entries[0].amount == 6
        assert entries[0].timing_points == 4
        assert entries[0].quality_points == 2


def test_total_award_never_exceeds_seven():
    assignment = _make_assignment("Pulse Cap Check", due_offset=timedelta(days=3))
    submission = _submit(assignment.id)
    result = _grade(submission["id"], quality=3)
    # 4 timing + 3 quality = 7, cap enforced
    assert result["points_awarded"] <= 7
    assert result["points_awarded"] == 7


def test_late_submission_never_gets_full_timing():
    assignment = _make_assignment(
        "Pulse Late Check",
        due_offset=timedelta(hours=-1),
        allow_late=True,
        late_window_hours=24,
    )
    submission = _submit(assignment.id)
    assert submission["is_late"] is True
    assert submission["timing_points"] == 1
    result = _grade(submission["id"], quality=3)
    assert result["points_awarded"] == 4  # 1 + 3, no on-time bonus


def test_duplicate_grade_requests_do_not_duplicate_awards():
    assignment = _make_assignment("Pulse Idempotency", due_offset=timedelta(days=3))
    submission = _submit(assignment.id)
    first = _grade(submission["id"], quality=2)
    assert first["points_awarded"] == 6

    with SessionLocal() as db:
        student_id = db.scalar(
            select(Student.id).where(Student.student_code == STUDENT_CODE)
        )
        count = len(
            list(
                db.scalars(
                    select(PulseLedgerEntry).where(
                        PulseLedgerEntry.student_id == student_id,
                        PulseLedgerEntry.txn_type == "award",
                    )
                )
            )
        )

    # Direct service-level retry must be a no-op (unique idempotency key).
    from app.services.pulse_points import award_for_submission

    with SessionLocal() as db:
        entry = award_for_submission(
            db,
            submission_id=submission["id"],
            student_id=student_id,
            assignment_id=assignment.id,
            timing_points=4,
            quality_points=2,
            actor_user_id=None,
        )
        db.commit()
        assert entry is None

    with SessionLocal() as db:
        count_after = len(
            list(
                db.scalars(
                    select(PulseLedgerEntry).where(
                        PulseLedgerEntry.student_id == student_id,
                        PulseLedgerEntry.txn_type == "award",
                    )
                )
            )
        )
        assert count_after == count


def test_balances_persist_and_reconcile_with_ledger():
    headers = student_headers()
    balance_view = client.get("/api/student/pulse/balance", headers=headers)
    assert balance_view.status_code == 200
    api_balance = balance_view.json()["balance"]

    with SessionLocal() as db:
        student_id = db.scalar(
            select(Student.id).where(Student.student_code == STUDENT_CODE)
        )
        result = reconcile_account(db, student_id)
        db.commit()
        assert result["balance"] == api_balance

    # A brand-new session sees the same persisted balance.
    with SessionLocal() as db:
        student = db.scalar(
            select(Student).where(Student.student_code == STUDENT_CODE)
        )
        from app.models.pulse_account import PulseAccount

        account = db.scalar(
            select(PulseAccount).where(PulseAccount.student_id == student.id)
        )
        assert account.balance == api_balance


def test_adjustments_and_reversals_are_auditable():
    with SessionLocal() as db:
        student = db.scalar(
            select(Student).where(Student.student_code == STUDENT_CODE)
        )
        student_id = student.id
        balance_before = client.get(
            "/api/student/pulse/balance", headers=student_headers()
        ).json()["balance"]

        entry = adjust_points(
            db,
            student_id=student_id,
            amount=3,
            txn_type="adjustment",
            reason="Test grading correction",
            actor_user_id=None,
            idempotency_key="test:pulse:adjustment:1",
        )
        db.commit()
        assert entry is not None and entry.amount == 3

        # Re-running the same adjustment key is a no-op.
        from app.services.pulse_points import adjust_points as adjust_again

        with SessionLocal() as db2:
            repeat = adjust_again(
                db2,
                student_id=student_id,
                amount=3,
                txn_type="adjustment",
                reason="Test grading correction",
                actor_user_id=None,
                idempotency_key="test:pulse:adjustment:1",
            )
            db2.commit()
            assert repeat is None

    balance_after = client.get(
        "/api/student/pulse/balance", headers=student_headers()
    ).json()["balance"]
    assert balance_after == balance_before + 3

    ledger = client.get(
        "/api/student/pulse/ledger?type=adjusted", headers=student_headers()
    )
    assert ledger.status_code == 200
    assert any(
        item["txn_type"] == "adjustment" and item["amount"] == 3
        for item in ledger.json()
    )
