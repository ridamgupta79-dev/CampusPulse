"""Teacher-side assignment management for authorized staff.

Object-level scope: teachers see and grade only submissions for assignments
they created. Cohort/subject authorization beyond ownership is a documented
prototype limitation (see docs/student-portal.md).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import get_current_user
from app.db.session import get_db
from app.models import Assignment, AssignmentSubmission, AuthUser, Student
from app.schemas.assignments import (
    AssignmentCreate,
    AssignmentRead,
    GradeSubmissionRequest,
)
from app.services.achievements import evaluate_submission_achievements
from app.services.pulse_points import (
    award_for_submission,
    create_notification,
    get_balance,
)

router = APIRouter(prefix="/teacher", tags=["Teacher Assignments"])

_ASSIGNMENT_CREATING_ROLES = {"faculty", "hod"}


def get_teacher_user(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Require a staff account with assignment-management privileges."""
    role = user.role.strip().lower()
    if role not in _ASSIGNMENT_CREATING_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only faculty or HOD accounts can manage assignments.",
        )
    return user


def _get_own_assignment(
    assignment_id: int,
    teacher: AuthUser,
    db: Session,
) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    if assignment.teacher_user_id != teacher.id:
        raise HTTPException(
            status_code=403,
            detail="You can only manage your own assignments.",
        )
    return assignment


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _iso_utc(value: datetime) -> str:
    """Serialize a stored timestamp as an explicit UTC ISO-8601 string.

    SQLite returns naive datetimes; the stored values are UTC, so the
    timezone is re-attached before serialization.
    """
    return _utc(value).isoformat()


@router.post("/assignments", status_code=201)
def create_assignment(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    teacher: AuthUser = Depends(get_teacher_user),
) -> dict:
    due_at = _utc(payload.due_at)

    status = "draft"
    published_at = None
    if payload.publish_now:
        status = "published"
        published_at = datetime.now(timezone.utc)

    assignment = Assignment(
        title=payload.title,
        description=payload.description,
        instructions=payload.instructions,
        subject=payload.subject,
        cohort=payload.cohort,
        teacher_user_id=teacher.id,
        status=status,
        published_at=published_at,
        due_at=due_at,
        max_marks=payload.max_marks,
        allow_late_submissions=payload.allow_late_submissions,
        late_window_hours=payload.late_window_hours,
    )
    db.add(assignment)
    db.flush()

    notified = 0
    if status == "published":
        notified = _notify_cohort_published(db, assignment)

    db.commit()
    db.refresh(assignment)

    return {
        "assignment": AssignmentRead.model_validate(assignment),
        "notified_students": notified,
        "message": (
            "Assignment published."
            if status == "published"
            else "Assignment saved as draft."
        ),
    }


def _notify_cohort_published(db: Session, assignment: Assignment) -> int:
    students = list(
        db.scalars(select(Student).where(Student.cohort == assignment.cohort))
    )
    for student in students:
        create_notification(
            db,
            student_id=student.id,
            category="assignment_published",
            title=f"New assignment: {assignment.title}",
            body=(
                f"{assignment.subject} — due "
                f"{_utc(assignment.due_at).isoformat()} (UTC)"
            ),
            assignment_id=assignment.id,
        )
    return len(students)


@router.get("/assignments")
def list_my_assignments(
    db: Session = Depends(get_db),
    teacher: AuthUser = Depends(get_teacher_user),
) -> list[dict]:
    assignments = list(
        db.scalars(
            select(Assignment)
            .where(Assignment.teacher_user_id == teacher.id)
            .order_by(Assignment.due_at.desc())
        )
    )

    result = []
    for assignment in assignments:
        submission_count = len(
            list(
                db.scalars(
                    select(AssignmentSubmission.id).where(
                        AssignmentSubmission.assignment_id == assignment.id,
                        AssignmentSubmission.status != "draft",
                    )
                )
            )
        )
        item = AssignmentRead.model_validate(assignment).model_dump(mode="json")
        item["submission_count"] = submission_count
        result.append(item)
    return result


@router.post("/assignments/{assignment_id}/publish")
def publish_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    teacher: AuthUser = Depends(get_teacher_user),
) -> dict:
    assignment = _get_own_assignment(assignment_id, teacher, db)
    if assignment.status != "draft":
        raise HTTPException(
            status_code=409,
            detail="Only draft assignments can be published.",
        )

    assignment.status = "published"
    assignment.published_at = datetime.now(timezone.utc)
    notified = _notify_cohort_published(db, assignment)
    db.commit()

    return {
        "id": assignment.id,
        "status": assignment.status,
        "notified_students": notified,
        "message": "Assignment published.",
    }


@router.post("/assignments/{assignment_id}/close")
def close_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    teacher: AuthUser = Depends(get_teacher_user),
) -> dict:
    assignment = _get_own_assignment(assignment_id, teacher, db)
    if assignment.status == "closed":
        raise HTTPException(
            status_code=409,
            detail="This assignment is already closed.",
        )

    assignment.status = "closed"
    db.commit()

    return {
        "id": assignment.id,
        "status": assignment.status,
        "message": "Assignment closed. New submissions are no longer accepted.",
    }


@router.get("/assignments/{assignment_id}/submissions")
def list_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
    teacher: AuthUser = Depends(get_teacher_user),
) -> list[dict]:
    assignment = _get_own_assignment(assignment_id, teacher, db)

    rows = list(
        db.scalars(
            select(AssignmentSubmission)
            .options(joinedload(AssignmentSubmission.student))
            .where(AssignmentSubmission.assignment_id == assignment.id)
            .order_by(AssignmentSubmission.submitted_at.desc())
        )
    )

    result = []
    for submission in rows:
        student = submission.student
        result.append(
            {
                "id": submission.id,
                "student_id": submission.student_id,
                "student_name": student.full_name if student else None,
                "student_code": student.student_code if student else None,
                "text_answer": submission.text_answer,
                "link_url": submission.link_url,
                "status": submission.status,
                "is_late": submission.is_late,
                "submitted_at": _iso_utc(submission.submitted_at),
                "marks_obtained": submission.marks_obtained,
                "quality_points": submission.quality_points,
                "timing_points": submission.timing_points,
                "feedback": submission.feedback,
                "feedback_released": submission.feedback_released,
                "resubmission_count": submission.resubmission_count,
            }
        )
    return result


@router.post("/submissions/{submission_id}/grade")
def grade_submission(
    submission_id: int,
    payload: GradeSubmissionRequest,
    db: Session = Depends(get_db),
    teacher: AuthUser = Depends(get_teacher_user),
) -> dict:
    submission = db.get(AssignmentSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")

    assignment = db.get(Assignment, submission.assignment_id)
    if assignment is None or assignment.teacher_user_id != teacher.id:
        raise HTTPException(
            status_code=403,
            detail="You can only grade submissions for your own assignments.",
        )

    if submission.status != "submitted":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only submitted work can be graded. Released grades are "
                "final in this prototype; corrections require a ledger "
                "adjustment."
            ),
        )

    marks = min(float(payload.marks_obtained), float(assignment.max_marks))
    submission.marks_obtained = marks
    submission.quality_points = payload.quality_points
    submission.feedback = payload.feedback
    submission.graded_by_user_id = teacher.id
    submission.graded_at = datetime.now(timezone.utc)

    balance_after = None
    unlocked: list[str] = []
    entry = None

    if payload.release:
        submission.status = "graded"
        submission.feedback_released = True

        timing = submission.timing_points or 0
        entry = award_for_submission(
            db,
            submission_id=submission.id,
            student_id=submission.student_id,
            assignment_id=assignment.id,
            timing_points=timing,
            quality_points=payload.quality_points,
            actor_user_id=teacher.id,
        )
        if entry is not None:
            balance_after = get_balance(db, submission.student_id)
            create_notification(
                db,
                student_id=submission.student_id,
                category="points_awarded",
                title="Pulse Points earned!",
                body=(
                    f"You earned {entry.amount} Pulse Points for "
                    f"{assignment.title}. {timing} point(s) for timing + "
                    f"{payload.quality_points} point(s) for submission quality."
                ),
                assignment_id=assignment.id,
                submission_id=submission.id,
            )
            create_notification(
                db,
                student_id=submission.student_id,
                category="feedback_released",
                title=f"Feedback released: {assignment.title}",
                body=payload.feedback or "Your work has been graded.",
                assignment_id=assignment.id,
                submission_id=submission.id,
            )
            unlocked = evaluate_submission_achievements(
                db,
                student_id=submission.student_id,
                is_synthetic=False,
            )
    else:
        submission.status = "returned"
        submission.feedback_released = False

    db.commit()

    return {
        "submission_id": submission.id,
        "status": submission.status,
        "marks_obtained": submission.marks_obtained,
        "quality_points": submission.quality_points,
        "feedback_released": submission.feedback_released,
        "points_awarded": entry.amount if payload.release and entry else 0,
        "balance_after": balance_after,
        "achievements_unlocked": unlocked,
        "message": (
            "Grade released to the student."
            if payload.release
            else "Grade saved as returned-for-revision feedback."
        ),
    }
