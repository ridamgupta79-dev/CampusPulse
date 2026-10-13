
import pytest
from fastapi import HTTPException

from app.services.intervention_workflow import (
    validate_intervention_status,
    validate_recommendation_decision,
)


def test_approved_decision_is_valid():
    assert validate_recommendation_decision("approved") == "approved"


def test_declined_decision_requires_reason():
    with pytest.raises(HTTPException) as exc_info:
        validate_recommendation_decision("declined")

    assert exc_info.value.status_code == 422


def test_declined_decision_with_reason_is_valid():
    assert (
        validate_recommendation_decision(
            "declined",
            "Support action is not appropriate at this time.",
        )
        == "declined"
    )


def test_invalid_recommendation_decision_is_rejected():
    with pytest.raises(HTTPException) as exc_info:
        validate_recommendation_decision("pending")

    assert exc_info.value.status_code == 422


def test_valid_intervention_status_is_normalized():
    assert validate_intervention_status(" IN_PROGRESS ") == "in_progress"


def test_invalid_intervention_status_is_rejected():
    with pytest.raises(HTTPException) as exc_info:
        validate_intervention_status("punished")

    assert exc_info.value.status_code == 422
