
"""Student endpoints, including the consent-aware Student 360 view."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import (
    PURPOSE_BY_DOMAIN,
    VISIBLE_SIGNAL_DOMAINS,
    can_view_signal_with_consent,
    get_current_staff_role,
)
from app.db.session import get_db
from app.models import Student
from app.models.student_consent import StudentConsent
from app.models.student_signal import StudentSignal
from app.schemas.student import StudentRead
from app.schemas.student_360 import (
    ConsentStatusRead,
    Student360Read,
    StudentSignalRead,
)

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("", response_model=list[StudentRead])
def list_students(
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> list[Student]:
    """List demo students (staff roles only)."""
    statement = select(Student).order_by(Student.student_code)
    return list(db.scalars(statement).all())


@router.get("/{student_id}", response_model=StudentRead)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> Student:
    """Retrieve a student's basic profile (staff roles only)."""
    student = db.get(Student, student_id)

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    return student


@router.get("/{student_id}/360", response_model=Student360Read)
def get_student_360(
    student_id: int,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> Student360Read:
    """Return a student overview filtered by role and consent.

    The role comes from the persisted account, so changing request headers
    or client state cannot widen access.
    """

    student = db.get(Student, student_id)

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    consent_statement = (
        select(StudentConsent)
        .where(StudentConsent.student_id == student_id)
        .order_by(StudentConsent.purpose)
    )
    consent_records = list(db.scalars(consent_statement).all())

    # Only explicitly granted consent permits signal access.
    consent_status_by_purpose = {
        consent.purpose: consent.status
        for consent in consent_records
    }

    signal_statement = (
        select(StudentSignal)
        .where(StudentSignal.student_id == student_id)
        .order_by(
            StudentSignal.domain,
            StudentSignal.recorded_at.desc(),
            StudentSignal.id.desc(),
        )
    )
    signal_records = list(db.scalars(signal_statement).all())

    visible_signals = [
        StudentSignalRead.model_validate(signal)
        for signal in signal_records
        if can_view_signal_with_consent(
            role=role,
            domain=signal.domain,
            consent_status_by_purpose=consent_status_by_purpose,
        )
    ]

    # Show only consent purposes relevant to this role.
    # Private consent notes are never returned.
    relevant_purposes = {
        PURPOSE_BY_DOMAIN[domain]
        for domain in VISIBLE_SIGNAL_DOMAINS[role]
        if domain in PURPOSE_BY_DOMAIN
    }

    visible_consents = [
        ConsentStatusRead.model_validate(consent)
        for consent in consent_records
        if consent.purpose in relevant_purposes
    ]

    return Student360Read(
        student=StudentRead.model_validate(student),
        consents=visible_consents,
        signals=visible_signals,
        viewer_role=role,
    )
