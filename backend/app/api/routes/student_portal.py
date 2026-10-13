"""Student portal endpoints.

Every endpoint resolves the caller's linked student record from the signed
token and the persisted account link, so object-level ownership is enforced
server-side on every request.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import (
    get_current_user,
    get_linked_student,
    get_student_link,
)
from app.db.session import get_db
from app.models import (
    Assignment,
    AssignmentSubmission,
    AuthUser,
    PulseAccount,
    Reward,
    RewardRedemption,
    Student,
    StudentAchievement,
    StudentNotification,
    StudentPortalProfile,
    StudentSignal,
    StudentSupportRequest,
)
from app.models.pulse_ledger import PulseLedgerEntry
from app.schemas.student_portal import (
    NotificationRead,
    PortalProfileUpdate,
    RedeemRequest,
    SubmissionCreate,
    SupportRequestCreate,
)
from app.services.achievements import (
    ACHIEVEMENT_META,
    evaluate_redemption_achievements,
    evaluate_submission_achievements,
)
from app.services.pulse_points import (
    compute_timing_points,
    create_notification,
    ensure_account,
    get_balance,
    net_earned,
    redeem_reward,
)

router = APIRouter(prefix="/student", tags=["Student Portal"])


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _iso_utc(value: datetime) -> str:
    """SQLite stores naive UTC datetimes; re-attach the zone on output."""
    return _utc(value).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_profile(db: Session, student_id: int) -> StudentPortalProfile:
    profile = db.scalar(
        select(StudentPortalProfile).where(
            StudentPortalProfile.student_id == student_id
        )
    )
    if profile is None:
        profile = StudentPortalProfile(student_id=student_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _profile_completion(student: Student, profile: StudentPortalProfile | None) -> int:
    fields = [
        True,  # name always present
        bool(student.program),
        bool(student.department),
        bool(student.cohort),
        bool(profile and profile.contact_email),
        bool(profile and profile.contact_phone),
        bool(profile and profile.bio),
        bool(profile and profile.skills),
        bool(profile and profile.certifications),
    ]
    return round(100 * sum(1 for present in fields if present) / len(fields))


# ---------------------------------------------------------------- me / home


@router.get("/me")
def get_me(
    user: AuthUser = Depends(get_current_user),
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    profile = _get_profile(db, student.id)
    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "student": _student_dict(student),
        "profile_completion": _profile_completion(student, profile),
    }


def _student_dict(student: Student) -> dict:
    return {
        "id": student.id,
        "student_code": student.student_code,
        "full_name": student.full_name,
        "program": student.program,
        "department": student.department,
        "year_of_study": student.year_of_study,
        "cohort": student.cohort,
        "advisor_name": student.advisor_name,
        "mentor_name": student.mentor_name,
    }


@router.get("/home")
def get_home(
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    now = _now()

    assignments = _visible_assignments(db, student)
    submissions = {
        submission.assignment_id: submission
        for submission in db.scalars(
            select(AssignmentSubmission).where(
                AssignmentSubmission.student_id == student.id
            )
        )
    }

    upcoming = [
        assignment
        for assignment in assignments
        if assignment.status == "published"
        and _utc(assignment.due_at) >= now
        and (assignment.id not in submissions
             or submissions[assignment.id].status == "draft")
    ]
    upcoming.sort(key=lambda a: _utc(a.due_at))

    graded = [
        submissions[a.id]
        for a in assignments
        if a.id in submissions and submissions[a.id].status == "graded"
    ]
    graded.sort(
        key=lambda s: _utc(s.graded_at or s.updated_at),
        reverse=True,
    )

    ensure_account(db, student.id)
    balance = get_balance(db, student.id)
    lifetime_earned = int(
        db.scalar(
            select(func.coalesce(func.sum(PulseLedgerEntry.amount), 0)).where(
                PulseLedgerEntry.student_id == student.id,
                PulseLedgerEntry.txn_type != "redemption",
            )
        )
        or 0
    )

    affordable_count = int(
        db.scalar(
            select(func.count(Reward.id)).where(
                Reward.is_active.is_(True),
                Reward.cost <= balance,
            )
        )
        or 0
    )

    pending_review = [
        submissions[a.id]
        for a in assignments
        if a.id in submissions and submissions[a.id].status == "submitted"
    ]

    achievements = list(
        db.scalars(
            select(StudentAchievement)
            .where(StudentAchievement.student_id == student.id)
            .order_by(StudentAchievement.earned_at.desc())
        )
    )

    notifications = list(
        db.scalars(
            select(StudentNotification)
            .where(StudentNotification.student_id == student.id)
            .order_by(StudentNotification.created_at.desc(),
                      StudentNotification.id.desc())
            .limit(8)
        )
    )
    unread_count = int(
        db.scalar(
            select(func.count(StudentNotification.id)).where(
                StudentNotification.student_id == student.id,
                StudentNotification.is_read.is_(False),
            )
        )
        or 0
    )

    support_requests = list(
        db.scalars(
            select(StudentSupportRequest)
            .where(StudentSupportRequest.student_id == student.id)
            .order_by(StudentSupportRequest.created_at.desc())
            .limit(5)
        )
    )

    _create_deadline_reminders(db, student, upcoming)

    attendance, average = _headline_academics(db, student)

    return {
        "student": _student_dict(student),
        "term": f"Year {student.year_of_study}",
        "attendance_percentage": attendance,
        "academic_average": average,
        "pending_assignments": len(pending_review),
        "due_soon_count": len(upcoming),
        "completed_assignments": len(graded),
        "pulse_balance": balance,
        "lifetime_earned": lifetime_earned,
        "affordable_rewards": affordable_count,
        "upcoming_deadlines": [
            {
                "assignment_id": a.id,
                "title": a.title,
                "subject": a.subject,
                "due_at": _iso_utc(a.due_at),
            }
            for a in upcoming[:5]
        ],
        "recent_feedback": [
            {
                "submission_id": s.id,
                "assignment_id": s.assignment_id,
                "assignment_title": next(
                    (
                        a.title
                        for a in assignments
                        if a.id == s.assignment_id
                    ),
                    None,
                ),
                "marks_obtained": s.marks_obtained,
                "max_marks": next(
                    (
                        a.max_marks
                        for a in assignments
                        if a.id == s.assignment_id
                    ),
                    None,
                ),
                "feedback": s.feedback,
                "graded_at": _iso_utc(s.graded_at) if s.graded_at else None,
            }
            for s in graded[:4]
        ],
        "achievements": [
            {
                "code": a.code,
                "title": ACHIEVEMENT_META.get(a.code, {}).get("title", a.code),
                "earned_at": _iso_utc(a.earned_at),
            }
            for a in achievements[:4]
        ],
        "notifications": [
            NotificationRead.model_validate(n).model_dump(mode="json")
            for n in notifications
        ],
        "unread_notifications": unread_count,
        "support_requests": [
            {
                "id": r.id,
                "request_type": r.request_type,
                "subject": r.subject,
                "status": r.status,
                "created_at": _iso_utc(r.created_at),
            }
            for r in support_requests
        ],
    }


def _visible_assignments(db: Session, student: Student) -> list[Assignment]:
    """Published or closed assignments for the student's own cohort."""
    now = _now()
    assignments = list(
        db.scalars(
            select(Assignment).where(
                Assignment.cohort == student.cohort,
                Assignment.status.in_(["published", "closed"]),
            )
        )
    )
    visible = [
        a
        for a in assignments
        if a.published_at is None
        or _utc(a.published_at) <= now
    ]
    return visible


def _headline_academics(db: Session, student: Student) -> tuple[float | None, float | None]:
    """Latest attendance percentage and assessment average, if recorded."""
    attendance = None
    average = None

    rows = list(
        db.scalars(
            select(StudentSignal)
            .where(StudentSignal.student_id == student.id)
            .order_by(StudentSignal.recorded_at.desc(), StudentSignal.id.desc())
        )
    )

    for signal in rows:
        if attendance is None and (
            signal.domain == "attendance"
            and signal.signal_name == "attendance_percentage"
            and signal.numeric_value is not None
        ):
            attendance = float(signal.numeric_value)
        if average is None and (
            signal.domain == "academics"
            and signal.signal_name == "assessment_average"
            and signal.numeric_value is not None
        ):
            average = float(signal.numeric_value)
        if attendance is not None and average is not None:
            break

    return attendance, average


def _create_deadline_reminders(
    db: Session,
    student: Student,
    upcoming: list[Assignment],
) -> None:
    """Persist one deadline-approaching notice per assignment (idempotent)."""
    now = _now()
    for assignment in upcoming:
        due = _utc(assignment.due_at)
        hours_left = (due - now).total_seconds() / 3600
        if hours_left > 48:
            continue

        existing = db.scalar(
            select(StudentNotification.id).where(
                StudentNotification.student_id == student.id,
                StudentNotification.assignment_id == assignment.id,
                StudentNotification.category == "deadline_approaching",
            )
        )
        if existing is not None:
            continue

        create_notification(
            db,
            student_id=student.id,
            category="deadline_approaching",
            title=f"Deadline approaching: {assignment.title}",
            body=(
                f"{assignment.subject} is due "
                f"{_iso_utc(assignment.due_at)} (UTC)."
            ),
            assignment_id=assignment.id,
        )
    db.commit()


# ------------------------------------------------------------- profile


@router.get("/profile")
def get_profile(
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    profile = _get_profile(db, student.id)

    enrolled_courses = sorted(
        {
            signal.text_value
            for signal in db.scalars(
                select(StudentSignal).where(
                    StudentSignal.student_id == student.id,
                    StudentSignal.domain == "academics",
                )
            )
            if signal.text_value
        }
    )

    return {
        "student": _student_dict(student),
        "profile": {
            "contact_email": profile.contact_email,
            "contact_phone": profile.contact_phone,
            "bio": profile.bio,
            "skills": profile.skills,
            "certifications": profile.certifications,
        },
        "enrolled_courses": enrolled_courses,
        "profile_completion": _profile_completion(student, profile),
    }


@router.patch("/profile")
def update_profile(
    payload: PortalProfileUpdate,
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    profile = _get_profile(db, student.id)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    return {
        "profile": {
            "contact_email": profile.contact_email,
            "contact_phone": profile.contact_phone,
            "bio": profile.bio,
            "skills": profile.skills,
            "certifications": profile.certifications,
        },
        "profile_completion": _profile_completion(student, profile),
        "message": "Profile updated.",
    }


@router.get("/academics")
def get_academics(
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    """The student's own permitted academic information.

    Confidential staff assessments, raw internal risk scores, and counselling
    records are never included; the student only sees their own signals and
    released assignment feedback.
    """
    signals = list(
        db.scalars(
            select(StudentSignal)
            .where(StudentSignal.student_id == student.id)
            .order_by(StudentSignal.recorded_at.desc(), StudentSignal.id.desc())
        )
    )

    by_domain: dict[str, list[dict]] = {}
    for signal in signals:
        by_domain.setdefault(signal.domain, []).append(
            {
                "signal_name": signal.signal_name,
                "numeric_value": signal.numeric_value,
                "text_value": signal.text_value,
                "recorded_at": _iso_utc(signal.recorded_at),
                "source_label": signal.source_label,
                "quality_status": signal.quality_status,
            }
        )

    assignments = _visible_assignments(db, student)
    submissions = {
        submission.assignment_id: submission
        for submission in db.scalars(
            select(AssignmentSubmission).where(
                AssignmentSubmission.student_id == student.id
            )
        )
    }

    assignment_grades = []
    for assignment in assignments:
        submission = submissions.get(assignment.id)
        if submission is None or not submission.feedback_released:
            continue
        assignment_grades.append(
            {
                "assignment_id": assignment.id,
                "title": assignment.title,
                "subject": assignment.subject,
                "marks_obtained": submission.marks_obtained,
                "max_marks": assignment.max_marks,
                "quality_points": submission.quality_points,
                "timing_points": submission.timing_points,
                "feedback": submission.feedback,
                "is_late": submission.is_late,
                "graded_at": (
                    _iso_utc(submission.graded_at)
                    if submission.graded_at
                    else None
                ),
            }
        )

    return {
        "student": _student_dict(student),
        "domains": by_domain,
        "assignment_grades": assignment_grades,
        "latest_attendance": _latest_numeric(
            by_domain, "attendance", "attendance_percentage"
        ),
        "latest_average": _latest_numeric(
            by_domain, "academics", "assessment_average"
        ),
        "note": (
            "This view shows your own recorded information only. Internal "
            "staff assessments and counselling notes are never included."
        ),
    }


def _latest_numeric(
    by_domain: dict[str, list[dict]],
    domain: str,
    signal_name: str,
) -> float | None:
    for entry in by_domain.get(domain, []):
        if entry["signal_name"] == signal_name and entry["numeric_value"] is not None:
            return float(entry["numeric_value"])
    return None


# ------------------------------------------------------------ assignments


@router.get("/assignments")
def list_assignments(
    filter: str = Query(
        default="all",
        pattern="^(all|upcoming|pending|submitted|graded)$",
    ),
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> list[dict]:
    now = _now()
    assignments = _visible_assignments(db, student)
    assignments.sort(key=lambda a: _utc(a.due_at))

    submissions = {
        submission.assignment_id: submission
        for submission in db.scalars(
            select(AssignmentSubmission).where(
                AssignmentSubmission.student_id == student.id
            )
        )
    }

    _create_deadline_reminders(
        db,
        student,
        [
            a
            for a in assignments
            if a.status == "published"
            and _utc(a.due_at) >= now
            and (a.id not in submissions
                 or submissions[a.id].status == "draft")
        ],
    )

    teacher_ids = {a.teacher_user_id for a in assignments}
    teachers = (
        {
            user.id: user.full_name
            for user in db.scalars(
                select(AuthUser).where(AuthUser.id.in_(teacher_ids))
            )
        }
        if teacher_ids
        else {}
    )

    items = []
    for assignment in assignments:
        submission = submissions.get(assignment.id)
        due = _utc(assignment.due_at)

        if submission is None:
            submission_state = "not_submitted"
            if assignment.status == "closed" or due < now:
                submission_state = "closed"
        else:
            submission_state = submission.status
            if submission_state == "submitted" and submission.is_late:
                submission_state = "submitted_late"

        if filter == "upcoming" and not (
            due >= now and submission_state in ("not_submitted", "draft")
        ):
            continue
        if filter == "pending" and submission_state not in (
            "not_submitted",
            "draft",
            "returned",
            "closed",
        ):
            continue
        if filter == "submitted" and submission_state not in (
            "submitted",
            "submitted_late",
        ):
            continue
        if filter == "graded" and submission_state != "graded":
            continue

        items.append(
            {
                "id": assignment.id,
                "title": assignment.title,
                "description": assignment.description,
                "instructions": assignment.instructions,
                "subject": assignment.subject,
                "teacher_name": teachers.get(assignment.teacher_user_id),
                "status": assignment.status,
                "published_at": (
                    _iso_utc(assignment.published_at)
                    if assignment.published_at
                    else None
                ),
                "due_at": _iso_utc(assignment.due_at),
                "max_marks": assignment.max_marks,
                "accepted_submission_types":
                    assignment.accepted_submission_types,
                "allow_late_submissions": assignment.allow_late_submissions,
                "submission_state": submission_state,
                "submission": (
                    _submission_dict(submission) if submission else None
                ),
            }
        )
    return items


def _submission_dict(submission: AssignmentSubmission) -> dict:
    return {
        "id": submission.id,
        "text_answer": submission.text_answer,
        "link_url": submission.link_url,
        "status": submission.status,
        "is_late": submission.is_late,
        "submitted_at": _iso_utc(submission.submitted_at),
        "resubmission_count": submission.resubmission_count,
        "marks_obtained": submission.marks_obtained,
        "timing_points": submission.timing_points,
        "quality_points": submission.quality_points,
        "feedback": (
            submission.feedback if submission.feedback_released else None
        ),
        "feedback_released": submission.feedback_released,
        "graded_at": (
            _iso_utc(submission.graded_at) if submission.graded_at else None
        ),
    }


@router.get("/assignments/{assignment_id}")
def get_assignment(
    assignment_id: int,
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    assignment = db.get(Assignment, assignment_id)
    if (
        assignment is None
        or assignment.cohort != student.cohort
        or assignment.status not in ("published", "closed")
    ):
        raise HTTPException(status_code=404, detail="Assignment not found.")

    submission = db.scalar(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.student_id == student.id,
        )
    )

    teacher = db.get(AuthUser, assignment.teacher_user_id)

    return {
        "id": assignment.id,
        "title": assignment.title,
        "description": assignment.description,
        "instructions": assignment.instructions,
        "subject": assignment.subject,
        "max_marks": assignment.max_marks,
        "allow_late_submissions": assignment.allow_late_submissions,
        "late_window_hours": assignment.late_window_hours,
        "status": assignment.status,
        "teacher_name": teacher.full_name if teacher else None,
        "cohort": assignment.cohort,
        "published_at": (
            _iso_utc(assignment.published_at)
            if assignment.published_at
            else None
        ),
        "due_at": _iso_utc(assignment.due_at),
        "accepted_submission_types": assignment.accepted_submission_types,
        "submission": _submission_dict(submission) if submission else None,
    }


@router.post("/assignments/{assignment_id}/submit")
def submit_assignment(
    assignment_id: int,
    payload: SubmissionCreate,
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    assignment = db.get(Assignment, assignment_id)
    if (
        assignment is None
        or assignment.cohort != student.cohort
        or assignment.status not in ("published", "closed")
    ):
        raise HTTPException(status_code=404, detail="Assignment not found.")

    now = _now()
    due = _utc(assignment.due_at)

    if not payload.text_answer and not payload.link_url:
        raise HTTPException(
            status_code=422,
            detail="Enter a written answer or a reference link.",
        )

    if assignment.status == "closed":
        raise HTTPException(
            status_code=409,
            detail=(
                "This assignment is closed and no longer accepts "
                "submissions."
            ),
        )

    submission = db.scalar(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.student_id == student.id,
        )
    )

    if submission is not None and submission.status == "graded":
        raise HTTPException(
            status_code=409,
            detail=(
                "This submission has already been graded and cannot be "
                "changed."
            ),
        )

    if payload.as_draft:
        if submission is None:
            submission = AssignmentSubmission(
                assignment_id=assignment.id,
                student_id=student.id,
                status="draft",
            )
            db.add(submission)
        submission.text_answer = payload.text_answer or ""
        submission.link_url = payload.link_url
        submission.status = "draft"
        db.commit()
        db.refresh(submission)
        return {
            "submission": _submission_dict(submission),
            "message": (
                "Draft saved. Submit before the deadline to earn Pulse "
                "Points."
            ),
        }

    is_late = False
    if due < now:
        late_window_seconds = assignment.late_window_hours * 3600
        if not assignment.allow_late_submissions:
            raise HTTPException(
                status_code=409,
                detail=(
                    "The deadline has passed and late submissions are not "
                    "allowed."
                ),
            )
        if (now - due).total_seconds() > late_window_seconds:
            raise HTTPException(
                status_code=409,
                detail=(
                    "The late-submission window for this assignment has "
                    "closed."
                ),
            )
        is_late = True

    published_at = (
        _utc(assignment.published_at) if assignment.published_at else now
    )
    timing_points = compute_timing_points(
        published_at=published_at,
        due_at=due,
        submitted_at=now,
        allow_late=assignment.allow_late_submissions,
        late_window_hours=assignment.late_window_hours,
    )
    if is_late:
        timing_points = min(timing_points, 1)

    if submission is None:
        submission = AssignmentSubmission(
            assignment_id=assignment.id,
            student_id=student.id,
        )
        db.add(submission)
    else:
        submission.resubmission_count += 1

    submission.text_answer = payload.text_answer or ""
    submission.link_url = payload.link_url
    submission.status = "submitted"
    submission.is_late = is_late
    submission.submitted_at = now
    submission.timing_points = timing_points

    db.flush()

    create_notification(
        db,
        student_id=student.id,
        category="submission_late" if is_late else "submission_received",
        title=(
            f"Late submission recorded: {assignment.title}"
            if is_late
            else f"Submission received: {assignment.title}"
        ),
        body=(
            "Your submission was recorded after the deadline."
            if is_late
            else (
                "Your submission was recorded. You can track its grading "
                "status."
            )
        ),
        assignment_id=assignment.id,
        submission_id=submission.id,
    )

    evaluate_submission_achievements(
        db,
        student_id=student.id,
        is_synthetic=False,
    )

    db.commit()
    db.refresh(submission)

    return {
        "submission": _submission_dict(submission),
        "message": (
            "Submission received."
            + (" Note: it is after the deadline." if is_late else "")
        ),
    }


# ---------------------------------------------------------- pulse points


@router.get("/pulse/balance")
def get_pulse_balance(
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    ensure_account(db, student.id)
    account = db.scalar(
        select(PulseAccount).where(PulseAccount.student_id == student.id)
    )

    pending_quality = int(
        db.scalar(
            select(func.count(AssignmentSubmission.id)).where(
                AssignmentSubmission.student_id == student.id,
                AssignmentSubmission.status == "submitted",
            )
        )
        or 0
    )

    return {
        "balance": account.balance,
        "lifetime_earned": account.lifetime_earned,
        "lifetime_redeemed": account.lifetime_redeemed,
        "pending_quality_reviews": pending_quality,
    }


@router.get("/pulse/ledger")
def get_pulse_ledger(
    type: str = Query(
        default="all",
        pattern="^(all|earned|redeemed|adjusted)$",
    ),
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> list[dict]:
    statement = (
        select(PulseLedgerEntry)
        .where(PulseLedgerEntry.student_id == student.id)
        .order_by(
            PulseLedgerEntry.created_at.desc(),
            PulseLedgerEntry.id.desc(),
        )
    )

    if type == "earned":
        statement = statement.where(PulseLedgerEntry.txn_type == "award")
    elif type == "redeemed":
        statement = statement.where(PulseLedgerEntry.txn_type == "redemption")
    elif type == "adjusted":
        statement = statement.where(
            PulseLedgerEntry.txn_type.in_(["adjustment", "reversal", "refund"])
        )

    entries = list(db.scalars(statement.limit(200)))

    assignment_ids = {e.assignment_id for e in entries if e.assignment_id}
    titles: dict[int, str] = {}
    if assignment_ids:
        titles = {
            a.id: a.title
            for a in db.scalars(
                select(Assignment).where(Assignment.id.in_(assignment_ids))
            )
        }

    return [
        {
            "id": entry.id,
            "txn_type": entry.txn_type,
            "amount": entry.amount,
            "reason": entry.reason,
            "assignment_id": entry.assignment_id,
            "assignment_title": titles.get(entry.assignment_id),
            "timing_points": entry.timing_points,
            "quality_points": entry.quality_points,
            "created_at": _iso_utc(entry.created_at),
        }
        for entry in entries
    ]


# ------------------------------------------------------------ marketplace


@router.get("/marketplace/leaderboard")
def get_leaderboard(
    cohort: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    """Live leaderboard computed from ledger aggregates in the database.

    Ranked by lifetime net earned points (redemptions do not reduce it;
    adjustments and reversals correct it). Ties share a rank and rows are
    ordered deterministically by student code.
    """
    net_subquery = (
        select(
            PulseLedgerEntry.student_id.label("student_id"),
            func.sum(PulseLedgerEntry.amount).label("net_earned"),
        )
        .where(PulseLedgerEntry.txn_type != "redemption")
        .group_by(PulseLedgerEntry.student_id)
        .subquery()
    )

    ranked = (
        select(
            net_subquery.c.student_id.label("student_id"),
            net_subquery.c.net_earned.label("net_earned"),
            func.rank()
            .over(order_by=net_subquery.c.net_earned.desc())
            .label("rank"),
        )
        .subquery()
    )

    base = (
        select(
            ranked.c.rank,
            ranked.c.net_earned,
            Student.id,
            Student.full_name,
            Student.cohort,
        )
        .join(Student, Student.id == ranked.c.student_id)
    )
    count_base = (
        select(func.count())
        .select_from(ranked)
        .join(Student, Student.id == ranked.c.student_id)
    )

    if cohort:
        base = base.where(Student.cohort == cohort)
        count_base = count_base.where(Student.cohort == cohort)

    total = int(db.scalar(count_base) or 0)

    rows = list(
        db.execute(
            base.order_by(
                ranked.c.net_earned.desc(),
                Student.student_code.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )

    own_row = db.execute(
        select(ranked.c.rank, ranked.c.net_earned).where(
            ranked.c.student_id == student.id
        )
    ).first()

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "cohort_filter": cohort,
        "entries": [
            {
                "rank": int(row.rank),
                "student_id": row.id,
                "display_name": row.full_name,
                "cohort": row.cohort,
                "net_earned": int(row.net_earned),
                "is_current_student": row.id == student.id,
            }
            for row in rows
        ],
        "me": {
            "rank": int(own_row.rank) if own_row else None,
            "net_earned": int(own_row.net_earned) if own_row else 0,
        },
        "metric_note": (
            "Ranked by lifetime net earned Pulse Points. Spending points "
            "does not lower your rank; corrections through adjustments and "
            "reversals do update it."
        ),
    }


@router.get("/marketplace/rewards")
def list_rewards(
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    balance = get_balance(db, student.id)
    rewards = list(
        db.scalars(
            select(Reward)
            .where(Reward.is_active.is_(True))
            .order_by(Reward.sort_order.asc(), Reward.cost.asc())
        )
    )

    return {
        "balance": balance,
        "rewards": [
            {
                "id": reward.id,
                "sku": reward.sku,
                "name": reward.name,
                "description": reward.description,
                "reward_type": reward.reward_type,
                "cost": reward.cost,
                "stock": reward.stock,
                "affordable": balance >= reward.cost,
                "points_needed": max(0, reward.cost - balance),
                "already_redeemed": db.scalar(
                    select(func.count(RewardRedemption.id)).where(
                        RewardRedemption.student_id == student.id,
                        RewardRedemption.reward_id == reward.id,
                        RewardRedemption.status == "completed",
                    )
                )
                > 0,
            }
            for reward in rewards
        ],
    }


@router.post("/marketplace/redeem")
def redeem(
    payload: RedeemRequest,
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    reward = db.get(Reward, payload.reward_id)
    if reward is None or not reward.is_active:
        raise HTTPException(
            status_code=404,
            detail="This reward is not available.",
        )

    redemption, message = redeem_reward(
        db,
        student_id=student.id,
        reward=reward,
    )

    if redemption is None:
        db.rollback()
        raise HTTPException(status_code=409, detail=message)

    create_notification(
        db,
        student_id=student.id,
        category="redemption_completed",
        title=f"Reward redeemed: {reward.name}",
        body=(
            f"{reward.cost} Pulse Points were deducted. Your redemption "
            f"reference is {redemption.reference}."
        ),
    )

    evaluate_redemption_achievements(db, student_id=student.id)

    db.commit()

    return {
        "reference": redemption.reference,
        "reward": {
            "id": reward.id,
            "name": reward.name,
            "cost": reward.cost,
            "reward_type": reward.reward_type,
        },
        "balance_after": get_balance(db, student.id),
        "message": message,
    }


@router.get("/marketplace/redemptions")
def list_redemptions(
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> list[dict]:
    redemptions = list(
        db.scalars(
            select(RewardRedemption)
            .where(RewardRedemption.student_id == student.id)
            .order_by(RewardRedemption.created_at.desc())
        )
    )

    reward_ids = {r.reward_id for r in redemptions}
    rewards = (
        {
            reward.id: reward
            for reward in db.scalars(
                select(Reward).where(Reward.id.in_(reward_ids))
            )
        }
        if reward_ids
        else {}
    )

    return [
        {
            "id": redemption.id,
            "reference": redemption.reference,
            "reward_name": rewards[redemption.reward_id].name
            if redemption.reward_id in rewards
            else None,
            "reward_type": rewards[redemption.reward_id].reward_type
            if redemption.reward_id in rewards
            else None,
            "cost": redemption.cost_at_redemption,
            "status": redemption.status,
            "created_at": _iso_utc(redemption.created_at),
        }
        for redemption in redemptions
    ]


# ---------------------------------------------------------- notifications


@router.get("/notifications")
def list_notifications(
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    notifications = list(
        db.scalars(
            select(StudentNotification)
            .where(StudentNotification.student_id == student.id)
            .order_by(
                StudentNotification.created_at.desc(),
                StudentNotification.id.desc(),
            )
            .limit(100)
        )
    )
    unread = int(
        db.scalar(
            select(func.count(StudentNotification.id)).where(
                StudentNotification.student_id == student.id,
                StudentNotification.is_read.is_(False),
            )
        )
        or 0
    )
    return {
        "unread": unread,
        "notifications": [
            NotificationRead.model_validate(n).model_dump(mode="json")
            for n in notifications
        ],
    }


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    updated = (
        db.query(StudentNotification)
        .filter(
            StudentNotification.student_id == student.id,
            StudentNotification.is_read.is_(False),
        )
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return {"updated": updated, "message": "All notifications marked as read."}


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    notification = db.get(StudentNotification, notification_id)
    if notification is None or notification.student_id != student.id:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notification.is_read = True
    db.commit()
    return {"id": notification.id, "is_read": True}


@router.get("/achievements")
def list_achievements(
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> list[dict]:
    achievements = list(
        db.scalars(
            select(StudentAchievement)
            .where(StudentAchievement.student_id == student.id)
            .order_by(StudentAchievement.earned_at.desc())
        )
    )
    return [
        {
            "code": achievement.code,
            "title": ACHIEVEMENT_META.get(achievement.code, {}).get(
                "title", achievement.code
            ),
            "description": ACHIEVEMENT_META.get(achievement.code, {}).get(
                "description", ""
            ),
            "earned_at": _iso_utc(achievement.earned_at),
        }
        for achievement in achievements
    ]


# ------------------------------------------------------------- support


@router.get("/support-requests")
def list_support_requests(
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> list[dict]:
    requests = list(
        db.scalars(
            select(StudentSupportRequest)
            .where(StudentSupportRequest.student_id == student.id)
            .order_by(StudentSupportRequest.created_at.desc())
        )
    )
    return [
        {
            "id": request.id,
            "request_type": request.request_type,
            "subject": request.subject,
            "details": request.details,
            "status": request.status,
            "response": request.student_visible_response,
            "created_at": _iso_utc(request.created_at),
            "updated_at": _iso_utc(request.updated_at),
        }
        for request in requests
    ]


@router.post("/support-requests", status_code=201)
def create_support_request(
    payload: SupportRequestCreate,
    student: Student = Depends(get_linked_student),
    db: Session = Depends(get_db),
) -> dict:
    request = StudentSupportRequest(
        student_id=student.id,
        request_type=payload.request_type,
        subject=payload.subject,
        details=payload.details,
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    return {
        "id": request.id,
        "status": request.status,
        "message": (
            "Support request submitted. A staff member will review it; "
            "requests are human-reviewed and never trigger automatic "
            "penalties."
        ),
    }
