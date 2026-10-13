"""Database-backed authentication for CampusPulse.

Passwords are PBKDF2-hashed and verified on login. Successful login and
registration return a signed, expiring JWT access token that every protected
route validates against the persisted account. Demo accounts are provisioned
only for local development/demo environments through ``seed_demo_users``.
"""
import base64, hashlib, hmac, secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.auth_user import AuthUser

router = APIRouter(prefix="/auth", tags=["Authentication"])
VALID_ROLES = {"student", "faculty", "mentor", "hod", "counsellor", "finance", "placement"}
STAFF_ROLES = {"faculty", "mentor", "hod", "counsellor", "finance", "placement"}
DEMO_PASSWORD = "CampusPulse@123"

def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return f"pbkdf2_sha256$240000${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"

def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, rounds, salt_b64, digest_b64 = stored.split("$")
        if scheme != "pbkdf2_sha256": return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), int(rounds))
        return hmac.compare_digest(actual, base64.b64decode(digest_b64))
    except (ValueError, TypeError):
        return False

def seed_demo_users(db: Session) -> None:
    """Provision the fixed demo accounts for non-production environments.

    Only missing accounts are created; existing rows (including their roles
    and passwords) are never modified.
    """
    accounts = [
        ("hod@campuspulse.demo", "CampusPulse HOD", "hod"),
        ("faculty@campuspulse.demo", "CampusPulse Faculty", "faculty"),
        ("mentor@campuspulse.demo", "CampusPulse Mentor", "mentor"),
        ("counsellor@campuspulse.demo", "CampusPulse Counsellor", "counsellor"),
        ("finance@campuspulse.demo", "CampusPulse Finance", "finance"),
        ("placement@campuspulse.demo", "CampusPulse Placement", "placement"),
    ]
    changed = False
    for email, name, role in accounts:
        if db.query(AuthUser).filter(AuthUser.email == email).first() is None:
            db.add(AuthUser(email=email, full_name=name, role=role, password_hash=_hash_password(DEMO_PASSWORD)))
            changed = True
    if changed: db.commit()


def _self_registration_roles() -> set[str]:
    return {
        part.strip().lower()
        for part in settings.self_registration_roles.split(",")
        if part.strip()
    }


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=256)
    full_name: str = Field(min_length=2, max_length=120)
    role: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@") or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Enter your full name.")
        return value

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in VALID_ROLES:
            raise ValueError("Select a valid CampusPulse role.")
        return value

class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=256)
    role: str


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create a persistent prototype account with a hashed password.

    Public self-registration is restricted to the configured low-privilege
    role(s); privileged roles require a trusted provisioning process.
    """
    email = payload.email.strip().lower()
    if payload.role not in _self_registration_roles():
        raise HTTPException(
            status_code=403,
            detail=(
                "Self-registration is not available for this role. "
                "Ask an administrator to provision privileged accounts."
            ),
        )
    existing = db.query(AuthUser).filter(AuthUser.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists. Sign in instead.")
    user = AuthUser(
        email=email,
        full_name=payload.full_name,
        role=payload.role,
        password_hash=_hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        # Handle a simultaneous registration for the same email gracefully.
        if db.query(AuthUser).filter(AuthUser.email == email).first():
            raise HTTPException(status_code=409, detail="An account with this email already exists. Sign in instead.")
        raise
    token = create_access_token(user.id, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role},
        "message": "Account created successfully.",
    }

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    seed_demo_users(db)
    if "@" not in payload.email or len(payload.email) > 254:
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    user = db.query(AuthUser).filter(AuthUser.email == payload.email.strip().lower()).first()
    if not user or not user.is_active or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    requested_role = payload.role.strip().lower()
    if requested_role not in VALID_ROLES or requested_role != user.role:
        raise HTTPException(status_code=403, detail="The selected role does not match this account.")
    token = create_access_token(user.id, user.role)
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}, "message": "Database credentials verified."}

@router.get("/demo-accounts")
def demo_accounts():
    """List the fixed local demo accounts.

    These accounts are only provisioned outside production, so this
    convenience endpoint is also disabled in production.
    """
    if settings.app_environment.strip().lower() == "production":
        raise HTTPException(status_code=404, detail="Not found.")
    return {"password": DEMO_PASSWORD, "accounts": [{"email": f"{role}@campuspulse.demo", "role": role} for role in ["hod", "faculty", "mentor", "counsellor", "finance", "placement"]], "note": "Local prototype accounts only. Change or remove before deployment."}
