"""Safe student-account-to-record enrollment.

A student account becomes usable only after it redeems a random, single-use
enrollment code that an authorized staff member (or the local demo seeder)
issued for one specific student record. Guessing a student code alone never
grants access to that record.
"""
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import get_current_staff_role, get_current_user
from app.db.session import get_db
from app.models import Student
from app.models.auth_user import AuthUser
from app.models.student_account_link import StudentAccountLink
from app.models.student_enrollment_code import StudentEnrollmentCode

router = APIRouter(tags=["Student Enrollment"])

_STAFF_CODE_ISSUING_ROLES = {"hod", "faculty"}


class EnrollRequest(BaseModel):
    student_code: str = Field(min_length=3, max_length=30)
    enrollment_code: str = Field(min_length=6, max_length=64)

    @field_validator("student_code", "enrollment_code")
    @classmethod
    def clean_value(cls, value: str) -> str:
        return value.strip()


class IssueEnrollmentCodeRequest(BaseModel):
    student_code: str = Field(min_length=3, max_length=30)

    @field_validator("student_code")
    @classmethod
    def clean_code(cls, value: str) -> str:
        return value.strip()


def _generate_enrollment_code() -> str:
    # Unambiguous alphabet, no visually confusable characters.
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "CP-" + "".join(secrets.choice(alphabet) for _ in range(8))


@router.post("/staff/enrollment-codes")
def issue_enrollment_code(
    payload: IssueEnrollmentCodeRequest,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
):
    """Issue a single-use enrollment code for one student record."""
    if role not in _STAFF_CODE_ISSUING_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only HOD or faculty accounts can issue enrollment codes.",
        )

    student = db.scalar(
        select(Student).where(Student.student_code == payload.student_code)
    )
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")

    code = _generate_enrollment_code()
    record = StudentEnrollmentCode(
        code=code,
        student_id=student.id,
    )
    db.add(record)
    db.commit()

    return {
        "enrollment_code": code,
        "student_code": student.student_code,
        "student_name": student.full_name,
        "note": (
            "Single-use code. Share it only with this student; it grants "
            "access to exactly this record."
        ),
    }


@router.get("/student/link-status")
def link_status(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Report whether the signed-in student account is linked to a record."""
    if user.role.strip().lower() != "student":
        return {"linked": False, "is_student": False}

    link = (
        db.query(StudentAccountLink)
        .filter(StudentAccountLink.user_id == user.id)
        .first()
    )
    if link is None:
        return {"linked": False, "is_student": True}

    student = db.get(Student, link.student_id)
    return {
        "linked": student is not None,
        "is_student": True,
        "student": {
            "id": student.id,
            "student_code": student.student_code,
            "full_name": student.full_name,
            "program": student.program,
            "department": student.department,
            "year_of_study": student.year_of_study,
            "cohort": student.cohort,
        }
        if student
        else None,
    }


@router.post("/student/enroll")
def enroll(
    payload: EnrollRequest,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Redeem an enrollment code to link this account to its student record."""
    if user.role.strip().lower() != "student":
        raise HTTPException(
            status_code=403,
            detail="Only student accounts can complete enrollment.",
        )

    existing_link = (
        db.query(StudentAccountLink)
        .filter(StudentAccountLink.user_id == user.id)
        .first()
    )
    if existing_link is not None:
        raise HTTPException(
            status_code=409,
            detail="This account is already linked to a student record.",
        )

    code_record = db.scalar(
        select(StudentEnrollmentCode).where(
            StudentEnrollmentCode.code == payload.enrollment_code
        )
    )
    if code_record is None or code_record.redeemed_by_user_id is not None:
        raise HTTPException(
            status_code=400,
            detail="This enrollment code is invalid or has already been used.",
        )

    student = db.get(Student, code_record.student_id)
    if student is None or student.student_code != payload.student_code:
        raise HTTPException(
            status_code=400,
            detail=(
                "This enrollment code does not match the student code "
                "provided."
            ),
        )

    link = StudentAccountLink(user_id=user.id, student_id=student.id)
    db.add(link)
    code_record.redeemed_by_user_id = user.id
    code_record.redeemed_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Enrollment could not be completed. Please try again.",
        )

    return {
        "linked": True,
        "student": {
            "id": student.id,
            "student_code": student.student_code,
            "full_name": student.full_name,
            "program": student.program,
            "department": student.department,
            "year_of_study": student.year_of_study,
            "cohort": student.cohort,
        },
        "message": "Enrollment complete. Welcome to CampusPulse.",
    }
