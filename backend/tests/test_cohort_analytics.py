
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.db.session import SessionLocal
from app.services.cohort_analytics import build_cohort_analytics


def test_cohort_analytics_returns_aggregate_structure():
    db = SessionLocal()
    try:
        result = build_cohort_analytics(db)

        assert result["student_count"] >= 0
        assert "assessment_coverage" in result
        assert "risk_distribution" in result
        assert "intervention_workload" in result
        assert "outcome_coverage" in result
        assert "data_quality" in result
        assert "interpretation_note" in result

        assert (
            result["assessment_coverage"]["assessed_students"]
            + result["assessment_coverage"]["students_without_assessment"]
            == result["student_count"]
        )
    finally:
        db.close()


def test_cohort_analytics_filters_by_cohort():
    db = SessionLocal()
    try:
        result = build_cohort_analytics(db, cohort="Cohort That Does Not Exist")
        assert result["student_count"] == 0
        assert result["risk_distribution"] == {}
        assert result["intervention_workload"]["total"] == 0
        assert result["outcome_coverage"]["recorded_outcomes"] == 0
    finally:
        db.close()


def test_cohort_analytics_rejects_invalid_stale_window():
    db = SessionLocal()
    try:
        with pytest.raises(ValueError):
            build_cohort_analytics(db, stale_after_days=0)
    finally:
        db.close()


def test_cohort_analytics_does_not_return_student_names():
    db = SessionLocal()
    try:
        result = build_cohort_analytics(db)

        assert "students" not in result
        assert "full_name" not in result
        assert "student_code" not in result
    finally:
        db.close()
