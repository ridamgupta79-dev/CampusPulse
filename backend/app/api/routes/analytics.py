
"""Role-protected cohort analytics endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.permissions import get_current_staff_role
from app.db.session import get_db
from app.services.cohort_analytics import build_cohort_analytics

router = APIRouter(prefix="/analytics", tags=["Cohort Analytics"])


@router.get("/cohort")
def get_cohort_analytics(
    cohort: str | None = Query(default=None, min_length=1, max_length=100),
    stale_after_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    role: str = Depends(get_current_staff_role),
) -> dict:
    """Return aggregate cohort metrics without student-level records."""

    if role != "hod":
        raise HTTPException(
            status_code=403,
            detail="Only the HOD demo role can access cohort analytics.",
        )

    result = build_cohort_analytics(
        db=db,
        cohort=cohort,
        stale_after_days=stale_after_days,
    )

    return result
