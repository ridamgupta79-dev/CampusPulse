"""Demo seeding: idempotency, referential integrity, and record preservation."""
from sqlalchemy import func, select

from conftest import client
from portal_helpers import login_headers

from app.db.session import SessionLocal
from app.models import (
    Assignment,
    AssignmentSubmission,
    Reward,
    RewardRedemption,
    Student,
    StudentAccountLink,
)
from app.models.auth_user import AuthUser
from app.models.pulse_ledger import PulseLedgerEntry
from app.seed.seed_student_portal_demo import seed_student_portal_demo


def _counts() -> dict:
    with SessionLocal() as db:
        return {
            "assignments": int(db.scalar(select(func.count(Assignment.id)))),
            "submissions": int(
                db.scalar(select(func.count(AssignmentSubmission.id)))
            ),
            "ledger": int(db.scalar(select(func.count(PulseLedgerEntry.id)))),
            "redemptions": int(
                db.scalar(select(func.count(RewardRedemption.id)))
            ),
            "links": int(db.scalar(select(func.count(StudentAccountLink.id)))),
        }


def test_demo_seed_is_idempotent_and_preserves_records():
    with SessionLocal() as db:
        students_before = int(db.scalar(select(func.count(Student.id))))

    seed_student_portal_demo()
    first = _counts()
    with SessionLocal() as db:
        users_after_first_seed = int(db.scalar(select(func.count(AuthUser.id))))
    seed_student_portal_demo()
    second = _counts()

    assert first == second, (first, second)

    with SessionLocal() as db:
        assert int(db.scalar(select(func.count(Student.id)))) == students_before
        # Idempotency means the second seed run adds no new accounts; the
        # first run may add demo users, so compare against post-first-seed.
        assert int(db.scalar(select(func.count(AuthUser.id)))) == users_after_first_seed

        for email, expected_role in [
            ("teacher@campuspulse.demo", "faculty"),
            ("aarav@campuspulse.demo", "student"),
            ("diya@campuspulse.demo", "student"),
            ("kabir@campuspulse.demo", "student"),
        ]:
            user = db.scalar(select(AuthUser).where(AuthUser.email == email))
            assert user is not None, email
            assert user.role == expected_role

        assignments = {a.id for a in db.scalars(select(Assignment)).all()}
        students = {s.id for s in db.scalars(select(Student)).all()}
        for submission in db.scalars(select(AssignmentSubmission)).all():
            assert submission.assignment_id in assignments
            assert submission.student_id in students

        # Deterministic leaderboard tie: Aarav and Diya both 29 net.
        net = (
            select(
                PulseLedgerEntry.student_id,
                func.sum(PulseLedgerEntry.amount).label("net"),
            )
            .where(PulseLedgerEntry.txn_type != "redemption")
            .group_by(PulseLedgerEntry.student_id)
            .subquery()
        )
        rows = list(
            db.execute(
                select(Student.student_code, net.c.net)
                .join(Student, Student.id == net.c.student_id)
                .where(
                    Student.student_code.in_(
                        ["CP-DEMO-0042", "CP-DEMO-0043", "CP-DEMO-0044"]
                    )
                )
            )
        )
        by_code = {code: int(value) for code, value in rows}
        assert by_code["CP-DEMO-0042"] == 29
        assert by_code["CP-DEMO-0043"] == 29
        assert by_code["CP-DEMO-0044"] == 6

        diya_user = db.scalar(
            select(AuthUser).where(AuthUser.email == "diya@campuspulse.demo")
        )
        diya_link = db.scalar(
            select(StudentAccountLink).where(
                StudentAccountLink.user_id == diya_user.id
            )
        )
        redemption = db.scalar(
            select(RewardRedemption).where(
                RewardRedemption.student_id == diya_link.student_id,
                RewardRedemption.status == "completed",
            )
        )
        assert redemption is not None
        assert redemption.reference.startswith("CP-RED-")

        bookstore = db.scalar(
            select(Reward).where(Reward.sku == "CP-RWD-BOOK-500")
        )
        assert bookstore.stock == 0


def test_demo_accounts_can_log_in_and_access_their_portal():
    response = client.post(
        "/api/auth/login",
        json={
            "email": "aarav@campuspulse.demo",
            "password": "CampusPulse@123",
            "role": "student",
        },
    )
    assert response.status_code == 200, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    me = client.get("/api/student/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["student"]["student_code"] == "CP-DEMO-0042"

    home = client.get("/api/student/home", headers=headers)
    assert home.status_code == 200
    assert home.json()["student"]["student_code"] == "CP-DEMO-0042"

    teacher_login = client.post(
        "/api/auth/login",
        json={
            "email": "teacher@campuspulse.demo",
            "password": "CampusPulse@123",
            "role": "faculty",
        },
    )
    assert teacher_login.status_code == 200
    teacher_headers = {
        "Authorization": f"Bearer {teacher_login.json()['access_token']}"
    }
    listing = client.get("/api/teacher/assignments", headers=teacher_headers)
    assert listing.status_code == 200
    assert len(listing.json()) >= 7
