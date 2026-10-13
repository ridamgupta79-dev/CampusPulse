
import logging

from fastapi import FastAPI

from app.core.config import settings
from app.core.security import ensure_security_configuration
from app.api.routes.students import router as students_router
from app.api.routes.recommendations import (
    router as recommendations_router,
)
from app.api.routes.interventions import router as interventions_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router, seed_demo_users
from app.api.routes.student_enrollment import router as enrollment_router
from app.api.routes.student_portal import router as student_portal_router
from app.api.routes.teacher_assignments import (
    router as teacher_assignments_router,
)
from app.api.routes.staff_support import router as staff_support_router
from app.api.routes.risk_assessments import (
    router as risk_assessments_router,
)
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app import models  # noqa: F401
from app.seed.seed_reward_catalogue import seed_reward_catalogue

logger = logging.getLogger("campuspulse")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "A student-success platform for explainable risk signals, "
        "coordinated interventions, and measurable follow-up outcomes."
    ),
)


# Initialize tables and, outside production, local demo identities.
@app.on_event("startup")
def initialize_database() -> None:
    # Fails startup in production when AUTH_JWT_SECRET is missing; logs a
    # warning in development when the ephemeral fallback secret is used.
    ensure_security_configuration()

    Base.metadata.create_all(bind=engine)

    if settings.app_environment.strip().lower() == "production":
        logger.info(
            "Production environment: demo account provisioning skipped."
        )
        return

    db = SessionLocal()
    try:
        seed_demo_users(db)
        # Additive, idempotent catalogue reference data for the student
        # marketplace. Never deletes or modifies existing rows.
        seed_reward_catalogue(db)
    finally:
        db.close()

# Register API routers.
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(
    students_router,
    prefix=settings.api_prefix,
)

app.include_router(
    recommendations_router,
    prefix=settings.api_prefix,
)

app.include_router(
    interventions_router,
    prefix=settings.api_prefix,
)

app.include_router(
    analytics_router,
    prefix=settings.api_prefix,
)

app.include_router(
    risk_assessments_router,
    prefix=settings.api_prefix,
)

app.include_router(enrollment_router, prefix=settings.api_prefix)
app.include_router(student_portal_router, prefix=settings.api_prefix)
app.include_router(teacher_assignments_router, prefix=settings.api_prefix)
app.include_router(staff_support_router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health", tags=["System"])
def health_check() -> dict[str, str]:
    """Check whether the API is running."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    """Return basic API information."""
    return {
        "message": "CampusPulse API is running.",
        "health": f"{settings.api_prefix}/health",
        "docs": "/docs",
    }
