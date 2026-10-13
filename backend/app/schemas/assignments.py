"""Schemas for teacher-side assignment management."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssignmentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(default="", max_length=4000)
    instructions: str = Field(default="", max_length=8000)
    subject: str = Field(min_length=1, max_length=100)
    cohort: str = Field(min_length=1, max_length=100)
    due_at: datetime
    max_marks: int = Field(default=100, ge=1, le=1000)
    allow_late_submissions: bool = True
    late_window_hours: int = Field(default=24, ge=0, le=336)
    publish_now: bool = True

    @field_validator("title", "subject", "cohort")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be empty.")
        return value


class AssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    instructions: str
    subject: str
    cohort: str
    status: str
    published_at: datetime | None
    due_at: datetime
    max_marks: int
    accepted_submission_types: str
    allow_late_submissions: bool
    late_window_hours: int
    created_at: datetime


class GradeSubmissionRequest(BaseModel):
    marks_obtained: float = Field(ge=0, le=1000)
    quality_points: int = Field(ge=0, le=3)
    feedback: str = Field(default="", max_length=4000)
    release: bool = True
