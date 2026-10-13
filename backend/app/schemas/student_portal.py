"""Schemas for the student portal endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StudentMeRead(BaseModel):
    user_id: int
    email: str
    student: dict
    profile_completion: int


class PortalProfileUpdate(BaseModel):
    contact_email: str | None = Field(default=None, max_length=254)
    contact_phone: str | None = Field(default=None, max_length=30)
    bio: str | None = Field(default=None, max_length=2000)
    skills: str | None = Field(default=None, max_length=2000)
    certifications: str | None = Field(default=None, max_length=2000)

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if value and ("@" not in value or value.startswith("@") or value.endswith("@")):
            raise ValueError("Enter a valid email address.")
        return value or None


class SubmissionCreate(BaseModel):
    text_answer: str = Field(default="", max_length=20000)
    link_url: str | None = Field(default=None, max_length=500)
    as_draft: bool = False

    @field_validator("text_answer", "link_url")
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class RedeemRequest(BaseModel):
    reward_id: int = Field(ge=1)


class SupportRequestCreate(BaseModel):
    request_type: str
    subject: str = Field(min_length=3, max_length=150)
    details: str = Field(default="", max_length=4000)

    @field_validator("request_type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        allowed = {"academic_checkin", "mentor_support", "assignment_clarification"}
        value = value.strip()
        if value not in allowed:
            raise ValueError("Select a supported request type.")
        return value

    @field_validator("subject")
    @classmethod
    def clean_subject(cls, value: str) -> str:
        return value.strip()


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    title: str
    body: str
    is_read: bool
    assignment_id: int | None
    created_at: datetime
