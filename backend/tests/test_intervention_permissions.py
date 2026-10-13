
import pytest

from app.core.permissions import can_review_recommendation


@pytest.mark.parametrize(
    ("actor_role", "intended_role", "expected"),
    [
        ("faculty", "faculty", True),
        ("mentor", "faculty", True),
        ("hod", "finance", True),
        ("finance", "finance", True),
        ("placement", "placement", True),
        ("faculty", "finance", False),
        ("placement", "counsellor", False),
        ("unknown", "faculty", False),
        ("faculty", "unknown", False),
    ],
)
def test_recommendation_review_permissions(
    actor_role,
    intended_role,
    expected,
):
    assert (
        can_review_recommendation(actor_role, intended_role)
        is expected
    )
