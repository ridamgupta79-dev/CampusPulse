"""Centralized role-visibility rules and authentication dependencies.

Role visibility and review policy live here; the authenticated identity is
resolved from a signed bearer token and the persisted account record, never
from a client-controlled header.
"""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core import security
from app.db.session import get_db
from app.models.auth_user import AuthUser
from app.models.student import Student
from app.models.student_account_link import StudentAccountLink


VISIBLE_SIGNAL_DOMAINS: dict[str, frozenset[str]] = {
    "faculty": frozenset({
        "attendance",
        "academics",
        "participation",
        "faculty_feedback",
    }),
    "mentor": frozenset({
        "attendance",
        "academics",
        "participation",
        "skills",
        "faculty_feedback",
    }),
    "hod": frozenset({
        "attendance",
        "academics",
        "participation",
        "skills",
        "faculty_feedback",
    }),
    "counsellor": frozenset(),
    "finance": frozenset({"fees"}),
    "placement": frozenset({"academics", "skills"}),
    # Students use the dedicated student-portal endpoints, not the staff
    # signal-domain views. The empty set keeps staff-only lookups fail-closed.
    "student": frozenset(),
}

STAFF_ROLES: frozenset[str] = frozenset(set(VISIBLE_SIGNAL_DOMAINS) - {"student"})


def get_visible_signal_domains(role: str) -> frozenset[str]:
    """Return the signal domains a recognized demo role may access."""
    normalized_role = role.strip().lower()

    if normalized_role not in VISIBLE_SIGNAL_DOMAINS:
        raise ValueError(f"Unknown demo role: {role}")

    return VISIBLE_SIGNAL_DOMAINS[normalized_role]


def can_view_signal(role: str, domain: str) -> bool:
    """Check whether a demo role may view a signal domain."""
    return domain.strip().lower() in get_visible_signal_domains(role)


def _bearer_authorization(
    authorization: str | None = Header(
        default=None,
        alias="Authorization",
    ),
) -> str | None:
    return authorization


def _raise_unauthorized(message: str) -> None:
    raise HTTPException(
        status_code=401,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Depends(_bearer_authorization),
) -> AuthUser:
    """Resolve the authenticated account from the bearer token.

    The token signature, expiry, and claims are validated first; the account
    is then loaded from the database so the persisted role and active status
    are authoritative. A role presented by the client is never trusted.
    """
    if not authorization:
        _raise_unauthorized("Authentication required.")

    scheme, _, credentials = authorization.partition(" ")
    if scheme.strip().lower() != "bearer" or not credentials.strip():
        _raise_unauthorized("A valid bearer token is required.")

    try:
        payload = security.decode_access_token(credentials.strip())
    except security.InvalidTokenError as exc:
        _raise_unauthorized(str(exc))

    user = db.get(AuthUser, int(payload["sub"]))

    if user is None or not user.is_active:
        _raise_unauthorized("Account not found or inactive.")

    return user


def get_current_role(
    user: AuthUser = Depends(get_current_user),
) -> str:
    """Return the persisted role of the authenticated account."""
    return user.role.strip().lower()


def get_current_staff_role(
    user: AuthUser = Depends(get_current_user),
) -> str:
    """Return the role for staff-only endpoints; students are rejected.

    Staff APIs (analytics, recommendations, interventions, risk assessments,
    the student directory) must not be reachable with a student account.
    """
    role = user.role.strip().lower()
    if role not in STAFF_ROLES:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is restricted to authorized staff roles.",
        )
    return role


def get_student_link(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudentAccountLink:
    """Resolve the account-to-record link for the authenticated student.

    Returns 403 for any account that is not a student or that has not yet
    completed enrollment, so ownership checks below the route always have a
    verified link available.
    """
    role = user.role.strip().lower()
    if role != "student":
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only available to student accounts.",
        )

    link = (
        db.query(StudentAccountLink)
        .filter(StudentAccountLink.user_id == user.id)
        .first()
    )

    if link is None:
        raise HTTPException(
            status_code=403,
            detail=(
                "This student account is not linked to a student record yet. "
                "Complete enrollment first."
            ),
        )

    return link


def get_linked_student(
    link: StudentAccountLink = Depends(get_student_link),
    db: Session = Depends(get_db),
) -> Student:
    """Load the exact student record an authenticated student is linked to."""
    student = db.get(Student, link.student_id)
    if student is None:
        raise HTTPException(
            status_code=403,
            detail="The linked student record no longer exists.",
        )
    return student


# Each signal domain is associated with its permitted purpose.
# Domains without a mapping are hidden by default.
PURPOSE_BY_DOMAIN: dict[str, str] = {
    "attendance": "academic_support",
    "academics": "academic_support",
    "participation": "academic_support",
    "faculty_feedback": "academic_support",
    "skills": "placement_support",
    "fees": "finance_support",
}


def can_view_signal_with_consent(
    role: str,
    domain: str,
    consent_status_by_purpose: dict[str, str],
) -> bool:
    """Require both role permission and explicitly granted consent."""
    normalized_domain = domain.strip().lower()
    required_purpose = PURPOSE_BY_DOMAIN.get(normalized_domain)

    if required_purpose is None:
        return False

    if not can_view_signal(role, normalized_domain):
        return False

    consent_status = consent_status_by_purpose.get(
        required_purpose,
        "unknown",
    )

    return consent_status.strip().lower() == "granted"


# Roles allowed to review recommendations for each intended staff role.
# HOD can review across categories as a demo oversight role.
RECOMMENDATION_REVIEW_ROLES: dict[str, frozenset[str]] = {
    "faculty": frozenset({"faculty", "mentor", "hod"}),
    "mentor": frozenset({"faculty", "mentor", "hod"}),
    "hod": frozenset({"hod"}),
    "counsellor": frozenset({"counsellor", "hod"}),
    "finance": frozenset({"finance", "hod"}),
    "placement": frozenset({"placement", "hod"}),
}


def can_review_recommendation(
    actor_role: str,
    intended_role: str,
) -> bool:
    """Check whether a demo role may review a recommendation.

    This is an authorization policy for the prototype, not authentication.
    """
    normalized_actor = actor_role.strip().lower()
    normalized_intended = intended_role.strip().lower()

    if normalized_actor not in VISIBLE_SIGNAL_DOMAINS:
        return False

    allowed_roles = RECOMMENDATION_REVIEW_ROLES.get(normalized_intended)

    if allowed_roles is None:
        return False

    return normalized_actor in allowed_roles
