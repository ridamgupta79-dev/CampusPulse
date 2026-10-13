
import pytest
from pydantic import ValidationError

from app.schemas.intervention_workflow import (
    InterventionAssignmentRequest,
    RecommendationReviewRequest,
)


def test_approved_review_request_is_valid():
    request = RecommendationReviewRequest(decision=" APPROVED ")

    assert request.decision == "approved"
    assert request.reason is None


def test_declined_review_request_normalizes_reason():
    request = RecommendationReviewRequest(
        decision="declined",
        reason="  Not appropriate at this time.  ",
    )

    assert request.decision == "declined"
    assert request.reason == "Not appropriate at this time."


def test_invalid_review_decision_is_rejected():
    with pytest.raises(ValidationError):
        RecommendationReviewRequest(decision="pending")


def test_unexpected_review_field_is_rejected():
    with pytest.raises(ValidationError):
        RecommendationReviewRequest(
            decision="approved",
            admin_override=True,
        )


def test_assignment_request_normalizes_fields():
    request = InterventionAssignmentRequest(
        assigned_role=" faculty ",
        assigned_owner=" Faculty Demo 01 ",
        due_date="2026-11-15T10:00:00",
        priority=" HIGH ",
    )

    assert request.assigned_role == "faculty"
    assert request.assigned_owner == "Faculty Demo 01"
    assert request.priority == "high"


def test_invalid_assignment_priority_is_rejected():
    with pytest.raises(ValidationError):
        InterventionAssignmentRequest(
            assigned_role="faculty",
            assigned_owner="Faculty Demo 01",
            due_date="2026-11-15T10:00:00",
            priority="critical",
        )


def test_blank_assignment_owner_is_rejected():
    with pytest.raises(ValidationError):
        InterventionAssignmentRequest(
            assigned_role="faculty",
            assigned_owner="   ",
            due_date="2026-11-15T10:00:00",
        )


from pydantic import ValidationError

from app.schemas.intervention_workflow import (
    InterventionFollowUpRequest,
    InterventionStatusUpdateRequest,
)


def test_follow_up_note_is_trimmed():
    payload = InterventionFollowUpRequest(
        note="  Student attended the scheduled mentoring session.  "
    )
    assert payload.note == (
        "Student attended the scheduled mentoring session."
    )


def test_follow_up_note_rejects_whitespace():
    with pytest.raises(ValidationError):
        InterventionFollowUpRequest(note="   ")


def test_follow_up_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        InterventionFollowUpRequest(
            note="Mentoring session completed.",
            extra_field="not allowed",
        )


def test_status_update_normalizes_status():
    payload = InterventionStatusUpdateRequest(status="  IN_PROGRESS  ")
    assert payload.status == "in_progress"


def test_status_update_rejects_unknown_status():
    with pytest.raises(ValidationError):
        InterventionStatusUpdateRequest(status="punished")


def test_status_update_normalizes_reason():
    payload = InterventionStatusUpdateRequest(
        status="cancelled",
        reason="  Student withdrew from the programme.  ",
    )
    assert payload.reason == "Student withdrew from the programme."


from pydantic import ValidationError

from app.schemas.intervention_workflow import InterventionOutcomeRequest


def test_outcome_schema_accepts_valid_measurements():
    payload = InterventionOutcomeRequest(
        metric_name="Assessment average",
        baseline_value=52,
        baseline_date="2026-10-08T10:00:00",
        follow_up_value=60,
        follow_up_date="2026-10-11T10:00:00",
        classification="improved",
        evidence_quality="medium",
        outcome_note="Illustrative follow-up measurement.",
    )

    assert payload.metric_name == "Assessment average"
    assert payload.baseline_value == 52
    assert payload.follow_up_value == 60
    assert payload.classification == "improved"


def test_outcome_schema_rejects_blank_metric_name():
    with pytest.raises(ValidationError):
        InterventionOutcomeRequest(metric_name="   ")


def test_outcome_schema_requires_baseline_date_with_value():
    with pytest.raises(ValidationError):
        InterventionOutcomeRequest(
            metric_name="Assessment average",
            baseline_value=52,
        )


def test_outcome_schema_requires_follow_up_date_with_value():
    with pytest.raises(ValidationError):
        InterventionOutcomeRequest(
            metric_name="Assessment average",
            follow_up_value=60,
        )


def test_outcome_schema_rejects_follow_up_before_baseline():
    with pytest.raises(ValidationError):
        InterventionOutcomeRequest(
            metric_name="Assessment average",
            baseline_value=52,
            baseline_date="2026-10-11T10:00:00",
            follow_up_value=60,
            follow_up_date="2026-10-08T10:00:00",
        )


def test_outcome_schema_rejects_unknown_evidence_quality():
    with pytest.raises(ValidationError):
        InterventionOutcomeRequest(
            metric_name="Assessment average",
            evidence_quality="perfect",
        )


def test_outcome_schema_rejects_unknown_classification():
    with pytest.raises(ValidationError):
        InterventionOutcomeRequest(
            metric_name="Assessment average",
            classification="guaranteed_success",
        )


