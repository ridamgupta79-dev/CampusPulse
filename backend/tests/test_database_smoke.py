
from sqlalchemy import inspect, select

from app.db.session import DATABASE_PATH, SessionLocal, engine
from app.models import (
    Intervention,
    InterventionEvent,
    InterventionOutcome,
    Recommendation,
    RiskAssessment,
    Student,
    StudentConsent,
    StudentSignal,
)


def test_database_file_exists():
    assert DATABASE_PATH.exists()


def test_all_eight_model_tables_exist():
    expected_tables = {
        "students",
        "student_consents",
        "student_signals",
        "risk_assessments",
        "recommendations",
        "interventions",
        "intervention_events",
        "intervention_outcomes",
    }

    actual_tables = set(inspect(engine).get_table_names())
    assert expected_tables.issubset(actual_tables)


def test_three_synthetic_students_exist():
    with SessionLocal() as db:
        codes = set(
            db.scalars(
                select(Student.student_code)
            ).all()
        )

    assert {
        "CP-DEMO-0042",
        "CP-DEMO-0043",
        "CP-DEMO-0044",
    }.issubset(codes)


def test_hero_student_has_complete_demo_workflow():
    with SessionLocal() as db:
        student = db.scalar(
            select(Student).where(
                Student.student_code == "CP-DEMO-0042"
            )
        )
        assert student is not None

        assessment = db.scalar(
            select(RiskAssessment).where(
                RiskAssessment.student_id == student.id
            )
        )
        recommendation = db.scalar(
            select(Recommendation).where(
                Recommendation.student_id == student.id
            )
        )
        intervention = db.scalar(
            select(Intervention).where(
                Intervention.student_id == student.id
            )
        )

        assert assessment is not None
        assert recommendation is not None
        assert intervention is not None

        events = db.scalars(
            select(InterventionEvent).where(
                InterventionEvent.intervention_id == intervention.id
            )
        ).all()

        outcomes = db.scalars(
            select(InterventionOutcome).where(
                InterventionOutcome.intervention_id == intervention.id
            )
        ).all()

        assert len(events) >= 5
        assert len(outcomes) >= 1


def test_missing_or_stale_signals_are_preserved():
    with SessionLocal() as db:
        signals = db.scalars(
            select(StudentSignal).where(
                StudentSignal.quality_status.in_(
                    ["missing", "stale"]
                )
            )
        ).all()

    assert signals, "Expected at least one missing or stale signal"


def test_consent_records_exist():
    with SessionLocal() as db:
        consents = db.scalars(
            select(StudentConsent)
        ).all()

    assert len(consents) >= 1


def test_placement_intervention_exists():
    with SessionLocal() as db:
        student = db.scalar(
            select(Student).where(
                Student.student_code == "CP-DEMO-0044"
            )
        )
        assert student is not None

        intervention = db.scalar(
            select(Intervention).where(
                Intervention.student_id == student.id,
                Intervention.intervention_type
                == "placement_readiness",
            )
        )

        assert intervention is not None
        assert intervention.status == "assigned"
