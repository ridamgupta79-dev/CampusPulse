
import pytest

from app.core.permissions import can_view_signal_with_consent


@pytest.mark.parametrize(
    ("role", "domain", "consents", "expected"),
    [
        ("faculty", "attendance", {"academic_support": "granted"}, True),
        ("faculty", "fees", {"finance_support": "granted"}, False),
        ("finance", "fees", {"finance_support": "granted"}, True),
        ("finance", "fees", {"finance_support": "unknown"}, False),
        ("finance", "fees", {}, False),
        ("placement", "skills", {"placement_support": "granted"}, True),
        ("placement", "skills", {"placement_support": "declined"}, False),
        ("faculty", "skills", {"placement_support": "granted"}, False),
        ("faculty", "attendance", {"academic_support": "withdrawn"}, False),
        ("faculty", "unknown_domain", {"academic_support": "granted"}, False),
    ],
)
def test_signal_visibility_requires_role_and_consent(
    role,
    domain,
    consents,
    expected,
):
    assert can_view_signal_with_consent(
        role,
        domain,
        consents,
    ) is expected
