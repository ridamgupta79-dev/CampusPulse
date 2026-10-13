"""Explicit, idempotent demo-data seeder for the Student Portal evaluation.

Run manually (never on startup):

    python -m app.seed.seed_student_portal_demo

The seeder is additive and safe to re-run: every object is keyed by a stable
identifier (email, cohort+title, unique submission pair, ledger idempotency
key, reward SKU) and skipped when it already exists. It never deletes or
modifies existing student records, accounts, or roles.

Demo dataset (all synthetic, labelled with is_synthetic=True):

- Teacher account  : teacher@campuspulse.demo   (faculty)
- Student accounts : aarav@campuspulse.demo  -> CP-DEMO-0042 (Aarav Mehta)
                     diya@campuspulse.demo   -> CP-DEMO-0043 (Diya Sharma)
                     kabir@campuspulse.demo  -> CP-DEMO-0044 (Kabir Verma)
- Seven assignments for cohort IT-Year-2 with mixed deadlines.
- On-time, late, awaiting-review, and graded submissions.
- Ledger awards: Aarav 29 net, Diya 29 net (leaderboard tie), Kabir 6.
- Diya has a completed redemption; the bookstore voucher stock is set to 0
  so an out-of-stock state is visible.
- Persistent notifications and achievements derived from the records above.

Passwords follow the shared local demo password documented in the README.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.auth import DEMO_PASSWORD, _hash_password
from app.db.init_db import create_tables
from app.db.session import SessionLocal
from app.models import (
    Assignment,
    AssignmentSubmission,
    AuthUser,
    Reward,
    RewardRedemption,
    Student,
    StudentAccountLink,
    StudentAchievement,
    StudentNotification,
    StudentSupportRequest,
)
from app.services.achievements import (
    evaluate_redemption_achievements,
    evaluate_submission_achievements,
)
from app.services.pulse_points import (
    award_for_submission,
    compute_timing_points,
    create_notification,
    ensure_account,
    redeem_reward,
)

TEACHER_EMAIL = "teacher@campuspulse.demo"
STUDENT_EMAILS = {
    "CP-DEMO-0042": "aarav@campuspulse.demo",
    "CP-DEMO-0043": "diya@campuspulse.demo",
    "CP-DEMO-0044": "kabir@campuspulse.demo",
}

HOURS = timedelta(hours=1)
DAYS = timedelta(days=1)


def _assignment_specs(now: datetime) -> list[dict]:
    return [
        {
            "key": "A1",
            "title": "Database Normalization Worksheet",
            "subject": "Database Systems",
            "description": "Apply 1NF, 2NF, and 3NF to the sample registrar "
                           "table and explain each step.",
            "instructions": "Write 300-500 words. Reference at least two "
                            "normal forms with examples.",
            "published_at": now - 6 * DAYS,
            "due_at": now - 2 * DAYS,
            "status": "closed",
            "max_marks": 20,
        },
        {
            "key": "A2",
            "title": "ER Diagram Case Study",
            "subject": "Database Systems",
            "description": "Design an ER diagram for the campus library "
                           "scenario and justify your design choices.",
            "instructions": "Submit your written answer; a reference link to "
                            "a shared diagram is optional.",
            "published_at": now - 3 * DAYS,
            "due_at": now + 4 * DAYS,
            "status": "published",
            "max_marks": 20,
        },
        {
            "key": "A3",
            "title": "SQL Practice Set 1",
            "subject": "Database Systems",
            "description": "Joins, aggregates, and grouping practice.",
            "instructions": "Answer all six questions in the worksheet.",
            "published_at": now - 12 * DAYS,
            "due_at": now - 5 * DAYS,
            "status": "closed",
            "max_marks": 30,
        },
        {
            "key": "A4",
            "title": "SQL Practice Set 2",
            "subject": "Database Systems",
            "description": "Subqueries and views practice.",
            "instructions": "Answer all five questions and include sample "
                            "outputs.",
            "published_at": now - 11 * DAYS,
            "due_at": now - 4 * DAYS,
            "status": "closed",
            "max_marks": 30,
        },
        {
            "key": "A5",
            "title": "Data Ethics Reflection",
            "subject": "Professional Practice",
            "description": "Reflect on responsible use of student data.",
            "instructions": "400-600 words. No references to real people.",
            "published_at": now - 10 * DAYS,
            "due_at": now - 3 * DAYS,
            "status": "closed",
            "max_marks": 20,
        },
        {
            "key": "A6",
            "title": "Orientation Week Survey",
            "subject": "Professional Practice",
            "description": "Short reflective survey about orientation week.",
            "instructions": "Three short paragraphs.",
            "published_at": now - 20 * DAYS,
            "due_at": now - 15 * DAYS,
            "status": "closed",
            "max_marks": 10,
        },
        {
            "key": "A7",
            "title": "SQL Query Practice (This Week)",
            "subject": "Database Systems",
            "description": "Write five SELECT queries against the demo "
                           "course schema and explain each in one line.",
            "instructions": "Submit as text. Late submissions are accepted "
                            "up to 24 hours after the deadline.",
            "published_at": now - 1 * DAYS,
            "due_at": now + 3 * DAYS,
            "status": "published",
            "max_marks": 25,
        },
    ]


# (assignment_key, student_code, hours_after_publish, quality, marks,
#  feedback) — timing is always computed from the recorded timestamps.
SUBMISSION_SPECS = [
    ("A1", "CP-DEMO-0042", 24.0, 2, 16,
     "Solid normalization steps. Add a closing summary next time."),
    ("A1", "CP-DEMO-0043", 97.0, 3, 17,
     "Submitted after the deadline but the analysis is thorough."),
    ("A2", "CP-DEMO-0042", 12.0, 3, 19,
     "Excellent diagram rationale. Full marks for justification."),
    ("A3", "CP-DEMO-0042", 24.0, 3, 27,
     "All joins correct; watch the GROUP BY edge case in Q5."),
    ("A3", "CP-DEMO-0043", 140.0, 3, 26,
     "Strong work across the set."),
    ("A3", "CP-DEMO-0044", 170.0, 2, 20,
     "Late submission; Q3 and Q4 need revision."),
    ("A4", "CP-DEMO-0042", 148.0, 2, 22,
     "Correct subqueries; the view definition needs an ORDER BY."),
    ("A4", "CP-DEMO-0043", 24.0, 3, 28,
     "Outstanding — clean views and sample outputs."),
    ("A5", "CP-DEMO-0042", 158.0, 2, 14,
     "Thoughtful reflection; add one concrete example."),
    ("A5", "CP-DEMO-0043", 24.0, 3, 18,
     "Excellent balance of benefits and risks."),
    ("A5", "CP-DEMO-0044", 158.0, 1, 11,
     "Short of the length requirement; see my notes."),
    ("A6", "CP-DEMO-0043", 24.0, 1, 6,
     "Complete but brief for the reflective questions."),
]


def _get_or_create_user(
    db: Session,
    email: str,
    full_name: str,
    role: str,
) -> AuthUser:
    user = db.scalar(select(AuthUser).where(AuthUser.email == email))
    if user is not None:
        return user
    user = AuthUser(
        email=email,
        full_name=full_name,
        role=role,
        password_hash=_hash_password(DEMO_PASSWORD),
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _notification_exists(
    db: Session,
    student_id: int,
    category: str,
    title: str,
) -> bool:
    return (
        db.scalar(
            select(StudentNotification.id).where(
                StudentNotification.student_id == student_id,
                StudentNotification.category == category,
                StudentNotification.title == title,
            )
        )
        is not None
    )


def seed_student_portal_demo() -> None:
    create_tables()

    with SessionLocal() as db:
        now = datetime.now(timezone.utc)

        teacher = _get_or_create_user(
            db, TEACHER_EMAIL, "Priya Nair (Demo Faculty)", "faculty"
        )

        students_by_code: dict[str, Student] = {}
        for student_code, email in STUDENT_EMAILS.items():
            student = db.scalar(
                select(Student).where(Student.student_code == student_code)
            )
            if student is None:
                raise RuntimeError(
                    f"Expected curated student {student_code} to exist. Run "
                    "app.seed.seed_students first."
                )
            students_by_code[student_code] = student
            _get_or_create_user(
                db,
                email,
                student.full_name,
                "student",
            )

        db.commit()

        # Account links (simulating a completed enrollment).
        for student_code, email in STUDENT_EMAILS.items():
            user = db.scalar(select(AuthUser).where(AuthUser.email == email))
            student = students_by_code[student_code]
            link = db.scalar(
                select(StudentAccountLink).where(
                    StudentAccountLink.user_id == user.id
                )
            )
            if link is None:
                db.add(StudentAccountLink(
                    user_id=user.id,
                    student_id=student.id,
                ))
        db.commit()

        # Assignments.
        assignments: dict[str, Assignment] = {}
        for spec in _assignment_specs(now):
            assignment = db.scalar(
                select(Assignment).where(
                    Assignment.cohort == "IT-Year-2",
                    Assignment.title == spec["title"],
                )
            )
            if assignment is None:
                assignment = Assignment(
                    title=spec["title"],
                    description=spec["description"],
                    instructions=spec["instructions"],
                    subject=spec["subject"],
                    cohort="IT-Year-2",
                    teacher_user_id=teacher.id,
                    status=spec["status"],
                    published_at=spec["published_at"],
                    due_at=spec["due_at"],
                    max_marks=spec["max_marks"],
                    allow_late_submissions=True,
                    late_window_hours=24,
                    is_synthetic=True,
                )
                db.add(assignment)
                db.flush()
                if spec["status"] == "published":
                    for student in students_by_code.values():
                        if not _notification_exists(
                            db,
                            student.id,
                            "assignment_published",
                            f"New assignment: {assignment.title}",
                        ):
                            create_notification(
                                db,
                                student_id=student.id,
                                category="assignment_published",
                                title=f"New assignment: {assignment.title}",
                                body=(
                                    f"{assignment.subject} — due "
                                    f"{assignment.due_at.isoformat()} (UTC)"
                                ),
                                assignment_id=assignment.id,
                                is_synthetic=True,
                            )
            assignments[spec["key"]] = assignment
        db.commit()

        # Submissions, grades, awards, notifications, achievements.
        for (
            key,
            student_code,
            hours_after_publish,
            quality,
            marks,
            feedback,
        ) in SUBMISSION_SPECS:
            assignment = assignments[key]
            student = students_by_code[student_code]

            existing = db.scalar(
                select(AssignmentSubmission).where(
                    AssignmentSubmission.assignment_id == assignment.id,
                    AssignmentSubmission.student_id == student.id,
                )
            )
            if existing is not None:
                continue

            published_at = assignment.published_at.replace(tzinfo=timezone.utc)
            due_at = assignment.due_at.replace(tzinfo=timezone.utc)
            submitted_at = published_at + timedelta(hours=hours_after_publish)
            is_late = submitted_at > due_at

            timing = compute_timing_points(
                published_at=published_at,
                due_at=due_at,
                submitted_at=submitted_at,
                allow_late=assignment.allow_late_submissions,
                late_window_hours=assignment.late_window_hours,
            )
            if is_late:
                timing = min(timing, 1)

            submission = AssignmentSubmission(
                assignment_id=assignment.id,
                student_id=student.id,
                text_answer=(
                    f"[Synthetic demo submission] {student.full_name}'s "
                    f"answer for {assignment.title}."
                ),
                status="submitted",
                is_late=is_late,
                submitted_at=submitted_at,
                timing_points=timing,
                is_synthetic=True,
            )
            db.add(submission)
            db.flush()

            # Grade and release immediately; this creates the award.
            submission.status = "graded"
            submission.marks_obtained = float(marks)
            submission.quality_points = quality
            submission.feedback = feedback
            submission.feedback_released = True
            submission.graded_by_user_id = teacher.id
            submission.graded_at = submitted_at + 2 * HOURS

            entry = award_for_submission(
                db,
                submission_id=submission.id,
                student_id=student.id,
                assignment_id=assignment.id,
                timing_points=timing,
                quality_points=quality,
                actor_user_id=teacher.id,
            )
            if entry is not None and not _notification_exists(
                db,
                student.id,
                "points_awarded",
                f"Pulse Points earned for {assignment.title}",
            ):
                create_notification(
                    db,
                    student_id=student.id,
                    category="points_awarded",
                    title=f"Pulse Points earned for {assignment.title}",
                    body=(
                        f"You earned {entry.amount} Pulse Points. {timing} "
                        f"point(s) for timing + {quality} point(s) for "
                        "submission quality."
                    ),
                    assignment_id=assignment.id,
                    submission_id=submission.id,
                    is_synthetic=True,
                )
                create_notification(
                    db,
                    student_id=student.id,
                    category="feedback_released",
                    title=f"Feedback released: {assignment.title}",
                    body=feedback,
                    assignment_id=assignment.id,
                    submission_id=submission.id,
                    is_synthetic=True,
                )

            evaluate_submission_achievements(
                db,
                student_id=student.id,
                is_synthetic=True,
            )
            db.commit()

        # One submission awaiting grading (Kabir, A2) so the "pending
        # quality review" state is visible.
        kabir = students_by_code["CP-DEMO-0044"]
        a2 = assignments["A2"]
        pending = db.scalar(
            select(AssignmentSubmission).where(
                AssignmentSubmission.assignment_id == a2.id,
                AssignmentSubmission.student_id == kabir.id,
            )
        )
        if pending is None:
            published_at = a2.published_at.replace(tzinfo=timezone.utc)
            due_at = a2.due_at.replace(tzinfo=timezone.utc)
            submitted_at = published_at + 24 * HOURS
            timing = compute_timing_points(
                published_at=published_at,
                due_at=due_at,
                submitted_at=submitted_at,
                allow_late=True,
                late_window_hours=24,
            )
            db.add(AssignmentSubmission(
                assignment_id=a2.id,
                student_id=kabir.id,
                text_answer=(
                    "[Synthetic demo submission] Kabir's ER diagram answer "
                    "awaiting teacher review."
                ),
                status="submitted",
                is_late=False,
                submitted_at=submitted_at,
                timing_points=timing,
                is_synthetic=True,
            ))
            db.flush()
            create_notification(
                db,
                student_id=kabir.id,
                category="submission_received",
                title=f"Submission received: {a2.title}",
                body=(
                    "Your submission was recorded. Quality points are "
                    "pending teacher review."
                ),
                assignment_id=a2.id,
                is_synthetic=True,
            )
            evaluate_submission_achievements(
                db,
                student_id=kabir.id,
                is_synthetic=True,
            )
            db.commit()

        # Diya's completed redemption of the 25-point badge.
        diya = students_by_code["CP-DEMO-0043"]
        badge = db.scalar(
            select(Reward).where(Reward.sku == "CP-RWD-BADGE-25")
        )
        already = db.scalar(
            select(RewardRedemption).where(
                RewardRedemption.student_id == diya.id,
                RewardRedemption.reward_id == badge.id,
                RewardRedemption.status == "completed",
            )
        )
        if already is None:
            redemption, message = redeem_reward(
                db,
                student_id=diya.id,
                reward=badge,
            )
            if redemption is not None:
                if not _notification_exists(
                    db,
                    diya.id,
                    "redemption_completed",
                    f"Reward redeemed: {badge.name}",
                ):
                    create_notification(
                        db,
                        student_id=diya.id,
                        category="redemption_completed",
                        title=f"Reward redeemed: {badge.name}",
                        body=(
                            f"{badge.cost} Pulse Points were deducted. Your "
                            f"redemption reference is {redemption.reference}."
                        ),
                        is_synthetic=True,
                    )
                evaluate_redemption_achievements(
                    db,
                    student_id=diya.id,
                    is_synthetic=True,
                )
            db.commit()

        # A visible out-of-stock reward for the demo.
        bookstore = db.scalar(
            select(Reward).where(Reward.sku == "CP-RWD-BOOK-500")
        )
        if bookstore is not None and bookstore.stock and bookstore.stock > 0:
            bookstore.stock = 0
            db.commit()

        # A resolved support request in Diya's history.
        if db.scalar(
            select(StudentSupportRequest.id).where(
                StudentSupportRequest.student_id == diya.id,
                StudentSupportRequest.subject
                == "Clarification: ER Diagram Case Study",
            )
        ) is None:
            db.add(StudentSupportRequest(
                student_id=diya.id,
                request_type="assignment_clarification",
                subject="Clarification: ER Diagram Case Study",
                details=(
                    "[Synthetic demo request] Could the diagram include "
                    "multivalued attributes, or should those be separate "
                    "entities?"
                ),
                status="resolved",
                assigned_role="faculty",
                student_visible_response=(
                    "Model them as separate entities with a relationship — "
                    "see the week 3 slide 12 example."
                ),
                is_synthetic=True,
            ))
            db.commit()

        # Summary of balances for the operator.
        for student_code, student in students_by_code.items():
            ensure_account(db, student.id)
        db.commit()

        print("Student Portal demo seed complete (idempotent).")
        print("  teacher@campuspulse.demo  role=faculty")
        for email in STUDENT_EMAILS.values():
            print(f"  {email}  role=student")
        print(f"  shared password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed_student_portal_demo()
