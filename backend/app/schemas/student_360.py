
"""Response schemas for the CampusPulse Student 360 view."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.student import StudentRead


class ConsentStatusRead(BaseModel):
    """Expose consent status without exposing private consent notes."""

    model_config = ConfigDict(from_attributes=True)

    purpose: str
    status: str
    recorded_at: datetime


class StudentSignalRead(BaseModel):
    """Represent a signal that has passed role and consent checks."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    domain: str
    signal_name: str
    numeric_value: float | None
    text_value: str | None
    recorded_at: datetime
    source_label: str | None
    quality_status: str
    purpose_category: str | None


class Student360Read(BaseModel):
    """Structured response for a role-filtered Student 360 view."""

    student: StudentRead
    consents: list[ConsentStatusRead]
    signals: list[StudentSignalRead]
    viewer_role: str
