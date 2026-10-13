"""Signed access-token handling for CampusPulse authentication.

Tokens are JSON Web Tokens signed with a server-side secret (HS256 by
default). The signing secret is read from configuration:

- Production deployments MUST set ``AUTH_JWT_SECRET``; startup fails loudly
  when it is missing.
- Development/demo environments may omit it, in which case an ephemeral
  per-process secret is generated so local tokens stay unforgeable within a
  single server run. This fallback never silently applies to production.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

logger = logging.getLogger("campuspulse.security")


class InvalidTokenError(Exception):
    """Raised when a presented access token cannot be trusted."""


_EPHEMERAL_SECRET: str | None = None


def _is_production() -> bool:
    return settings.app_environment.strip().lower() == "production"


def get_signing_secret() -> str:
    """Return the configured signing secret.

    In production a missing secret is a hard configuration error. In other
    environments a per-process ephemeral secret is generated once and reused
    so tokens remain valid across requests but die with the process.
    """
    global _EPHEMERAL_SECRET

    configured = settings.auth_jwt_secret.strip()
    if configured:
        return configured

    if _is_production():
        raise RuntimeError(
            "AUTH_JWT_SECRET is not configured. Refusing to sign tokens in "
            "production without an explicitly configured secret."
        )

    if _EPHEMERAL_SECRET is None:
        _EPHEMERAL_SECRET = secrets.token_urlsafe(64)

    return _EPHEMERAL_SECRET


def ensure_security_configuration() -> None:
    """Validate security settings at startup; raise when misconfigured."""
    secret = get_signing_secret()
    if settings.auth_jwt_secret.strip() and len(secret) < 32:
        logger.warning(
            "AUTH_JWT_SECRET is shorter than 32 bytes; use a longer secret."
        )


def create_access_token(
    user_id: int,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Mint a signed, expiring access token for an authenticated account."""
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.auth_access_token_expire_minutes,
        )

    payload = {
        "sub": str(user_id),
        "role": role,
        "typ": "access",
        "iat": now,
        "exp": now + expires_delta,
        "jti": secrets.token_hex(16),
    }

    return jwt.encode(
        payload,
        get_signing_secret(),
        algorithm=settings.auth_jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    """Validate signature, expiry, and required claims; return the payload."""
    if not token or not token.strip():
        raise InvalidTokenError("Token is empty.")

    try:
        payload = jwt.decode(
            token.strip(),
            get_signing_secret(),
            algorithms=[settings.auth_jwt_algorithm],
            options={"require": ["exp", "sub", "iat"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Token is invalid.") from exc

    if payload.get("typ") != "access":
        raise InvalidTokenError("Token is not an access token.")

    if not str(payload.get("sub", "")).strip().isdigit():
        raise InvalidTokenError("Token subject is invalid.")

    return payload
