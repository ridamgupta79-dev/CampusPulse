"""Staff-side review of student support requests.

Requests are human-reviewed: this is the only path that changes their status
or adds a response. Internal staff notes stay staff-only; students see only
``student_visible_response``.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import get_current_staff_role
from app.db.session import get_db
from app.models import Student, StudentSupportRequest

router = APIRouter(prefix="/staff", tags=["Staff Support"])

_REVIEW_ROLES = {"hod", "faculty", "mentor", "counsellor"}


class SupportReviewRequest(BaseModel):
    status: str = Field(pattern="^(open|in_review|resolved)$")
    student_visible_response: str | None = Field(
        default=None,
        max_length=4000,
    )
    staff_internal_note: str | None = Field(default=None, max_length=4000)


@router.get("/support-requests")
def list_support_requests(
    status: str | None = None,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> list[dict]:
    if role not in _REVIEW_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Your role cannot review support requests.",
        )

    statement = (
        select(StudentSupportRequest, Student)
        .join(Student, Student.id == StudentSupportRequest.student_id)
        .order_by(StudentSupportRequest.created_at.desc())
        .limit(200)
    )
    if status:
        statement = statement.where(StudentSupportRequest.status == status)

    rows = list(db.execute(statement))
    return [
        {
            "id": request.id,
            "student_name": student.full_name,
            "student_code": student.student_code,
            "request_type": request.request_type,
            "subject": request.subject,
            "details": request.details,
            "status": request.status,
            "created_at": request.created_at.isoformat(),
        }
        for request, student in rows
    ]


@router.patch("/support-requests/{request_id}")
def review_support_request(
    request_id: int,
    payload: SupportReviewRequest,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> dict:
    if role not in _REVIEW_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Your role cannot review support requests.",
        )

    request = db.get(StudentSupportRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Support request not found.")

    request.status = payload.status
    if payload.student_visible_response is not None:
        request.student_visible_response = payload.student_visible_response
    if payload.staff_internal_note is not None:
        request.staff_internal_note = payload.staff_internal_note

    db.commit()

    return {
        "id": request.id,
        "status": request.status,
        "message": "Support request updated.",
    }
