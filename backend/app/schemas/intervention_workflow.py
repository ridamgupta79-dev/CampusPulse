
"""Request schemas for intervention workflow actions."""

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class RecommendationReviewRequest(BaseModel):
    """A human decision on a proposed student-support recommendation."""

    model_config = ConfigDict(extra="forbid")

    decision: str = Field(
        description="Either approved or declined.",
    )
    reason: str | None = Field(
        default=None,
        max_length=2000,
        description="Reason for the decision; required when declining.",
    )

    @field_validator("decision")
    @classmethod
    def normalize_decision(cls, value: str) -> str:
        normalized = value.strip().lower()

        if normalized not in {"approved", "declined"}:
            raise ValueError(
                "Decision must be 'approved' or 'declined'."
            )

        return normalized

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class InterventionAssignmentRequest(BaseModel):
    """Details required to assign an approved intervention."""

    model_config = ConfigDict(extra="forbid")

    assigned_role: str = Field(min_length=1, max_length=40)
    assigned_owner: str = Field(min_length=1, max_length=120)
    due_date: datetime
    supporting_role: str | None = Field(
        default=None,
        max_length=40,
    )
    priority: str = Field(default="medium", max_length=20)

    @field_validator("assigned_role", "assigned_owner")
    @classmethod
    def validate_nonblank(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("This field cannot be blank.")

        return normalized

    @field_validator("priority")
    @classmethod
    def normalize_priority(cls, value: str) -> str:
        normalized = value.strip().lower()

        if normalized not in {"low", "medium", "high", "urgent"}:
            raise ValueError(
                "Priority must be low, medium, high, or urgent."
            )

        return normalized


class InterventionFollowUpRequest(BaseModel):
    """A note documenting intervention follow-up."""

    model_config = ConfigDict(extra="forbid")

    note: str = Field(min_length=1, max_length=4000)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("A follow-up note cannot be blank.")
        return normalized


class InterventionStatusUpdateRequest(BaseModel):
    """A requested intervention status transition."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1, max_length=30)
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {
            "approved",
            "assigned",
            "in_progress",
            "follow_up_recorded",
            "measured",
            "completed",
            "cancelled",
        }
        if normalized not in allowed:
            raise ValueError("Unrecognized intervention status.")
        return normalized

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class InterventionOutcomeRequest(BaseModel):
    """A measured or documented intervention outcome."""

    model_config = ConfigDict(extra="forbid")

    metric_name: str = Field(min_length=1, max_length=100)
    baseline_value: float | None = None
    baseline_date: datetime | None = None
    follow_up_value: float | None = None
    follow_up_date: datetime | None = None

    classification: str = Field(
        default="insufficient_evidence",
        max_length=40,
    )
    outcome_note: str | None = Field(default=None, max_length=4000)
    evidence_quality: str = Field(default="unknown", max_length=40)

    @field_validator("metric_name")
    @classmethod
    def validate_metric_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Metric name cannot be blank.")
        return normalized

    @field_validator("classification")
    @classmethod
    def normalize_classification(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {
            "improved",
            "unchanged",
            "declined",
            "mixed",
            "insufficient_evidence",
        }
        if normalized not in allowed:
            raise ValueError("Unrecognized outcome classification.")
        return normalized

    @field_validator("evidence_quality")
    @classmethod
    def normalize_evidence_quality(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"high", "medium", "low", "unknown"}:
            raise ValueError("Unrecognized evidence quality.")
        return normalized

    @field_validator("outcome_note")
    @classmethod
    def normalize_outcome_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_measurement_dates(self):
        if (self.baseline_value is None) != (self.baseline_date is None):
            raise ValueError(
                "Baseline value and date must either both be supplied "
                "or both be omitted."
            )

        if (self.follow_up_value is None) != (self.follow_up_date is None):
            raise ValueError(
                "Follow-up value and date must either both be supplied "
                "or both be omitted."
            )

        if (
            self.baseline_date is not None
            and self.follow_up_date is not None
            and self.follow_up_date < self.baseline_date
        ):
            raise ValueError(
                "Follow-up date cannot precede the baseline date."
            )

        return self


