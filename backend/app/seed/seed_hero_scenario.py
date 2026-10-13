
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.init_db import create_tables
from app.db.session import SessionLocal
from app.models import (
    Intervention,
    InterventionEvent,
    InterventionOutcome,
    Recommendation,
    RiskAssessment,
    Student,
    StudentSignal,
)


def utc(year: int, month: int, day: int) -> datetime:
    """Create a fixed UTC timestamp for reproducible demo records."""
    return datetime(year, month, day, tzinfo=timezone.utc)


def seed_hero_scenario() -> None:
    """Seed the hero student's assessment and intervention workflow."""
    create_tables()

    with SessionLocal() as db:
        student = db.scalar(
            select(Student).where(
                Student.student_code == "CP-DEMO-0042"
            )
        )

        if student is None:
            raise RuntimeError(
                "Run seed_students and seed_context before this command."
            )

        signals = db.scalars(
            select(StudentSignal).where(
                StudentSignal.student_id == student.id
            )
        ).all()

        attendance = [
            s for s in signals
            if s.signal_name == "attendance_percentage"
            and s.quality_status == "valid"
        ]
        academics = [
            s for s in signals
            if s.signal_name == "assessment_average"
            and s.quality_status == "valid"
        ]

        if len(attendance) < 2 or len(academics) < 2:
            raise RuntimeError(
                "Hero student needs earlier and recent attendance "
                "and assessment signals. Run seed_context first."
            )

        assessment = db.scalar(
            select(RiskAssessment).where(
                RiskAssessment.student_id == student.id,
                RiskAssessment.rule_version == "demo-rules-v1",
            )
        )

        if assessment is None:
            assessment = RiskAssessment(
                student_id=student.id,
                score=None,
                risk_band="needs_review",
                factor_breakdown=[
                    {
                        "signal": "attendance_percentage",
                        "earlier_value": 78,
                        "recent_value": 61,
                        "change": -17,
                        "rationale": (
                            "The observed attendance decline "
                            "warrants contextual review."
                        ),
                    },
                    {
                        "signal": "assessment_average",
                        "earlier_value": 68,
                        "recent_value": 52,
                        "change": -16,
                        "rationale": (
                            "The observed assessment decline "
                            "warrants an academic support review."
                        ),
                    },
                ],
                data_quality_notes=[
                    {
                        "signal": "participation_activity",
                        "quality_status": "missing",
                        "note": (
                            "Participation is unknown and was "
                            "not used as negative evidence."
                        ),
                    }
                ],
                rule_version="demo-rules-v1",
                summary=(
                    "Synthetic review-priority assessment. "
                    "This is not a validated prediction."
                ),
                assessed_at=utc(2026, 10, 8),
            )
            db.add(assessment)
            db.flush()

        recommendation = db.scalar(
            select(Recommendation).where(
                Recommendation.student_id == student.id,
                Recommendation.assessment_id == assessment.id,
                Recommendation.intervention_type
                == "academic_support",
            )
        )

        if recommendation is None:
            recommendation = Recommendation(
                student_id=student.id,
                assessment_id=assessment.id,
                intervention_type="academic_support",
                rationale=(
                    "Recent attendance and assessment declines "
                    "justify offering supportive academic review."
                ),
                contributing_signals=[
                    "attendance_percentage",
                    "assessment_average",
                    "pending_lab_submissions",
                ],
                intended_role="faculty",
                suggested_next_step=(
                    "Offer a faculty check-in, review pending lab "
                    "submissions, and coordinate a mentor check-in."
                ),
                priority="high",
                status="approved",
                decision_reason=(
                    "Synthetic demo decision: academic support "
                    "approved for demonstration."
                ),
                created_at=utc(2026, 10, 8),
                updated_at=utc(2026, 10, 8),
            )
            db.add(recommendation)
            db.flush()

        intervention = db.scalar(
            select(Intervention).where(
                Intervention.recommendation_id == recommendation.id
            )
        )

        if intervention is None:
            intervention = Intervention(
                student_id=student.id,
                recommendation_id=recommendation.id,
                intervention_type="academic_support",
                description=(
                    "Review pending lab submissions, offer "
                    "academic support, and conduct a mentor check-in."
                ),
                assigned_role="faculty",
                assigned_owner="Faculty Demo 01",
                supporting_role="mentor",
                due_date=utc(2026, 10, 15),
                status="measured",
                priority="high",
                created_at=utc(2026, 10, 8),
                updated_at=utc(2026, 10, 11),
            )
            db.add(intervention)
            db.flush()

        event_definitions = [
            (
                "approved",
                "faculty",
                "Faculty Demo 01",
                utc(2026, 10, 8),
                "Synthetic recommendation approved.",
            ),
            (
                "assigned",
                "faculty",
                "Faculty Demo 01",
                utc(2026, 10, 8),
                "Intervention assigned with a due date.",
            ),
            (
                "started",
                "faculty",
                "Faculty Demo 01",
                utc(2026, 10, 9),
                "Academic support workflow started in the demo.",
            ),
            (
                "follow_up_recorded",
                "mentor",
                "Mentor Demo 01",
                utc(2026, 10, 11),
                "Illustrative follow-up event for the synthetic scenario.",
            ),
            (
                "outcome_recorded",
                "faculty",
                "Faculty Demo 01",
                utc(2026, 10, 11),
                "Illustrative outcome recorded; not causal evidence.",
            ),
        ]

        for event_type, role, actor, occurred_at, note in event_definitions:
            existing = db.scalar(
                select(InterventionEvent).where(
                    InterventionEvent.intervention_id == intervention.id,
                    InterventionEvent.event_type == event_type,
                    InterventionEvent.occurred_at == occurred_at,
                )
            )

            if existing is None:
                db.add(
                    InterventionEvent(
                        intervention_id=intervention.id,
                        event_type=event_type,
                        actor_role=role,
                        actor_label=actor,
                        occurred_at=occurred_at,
                        note=note,
                    )
                )

        outcome = db.scalar(
            select(InterventionOutcome).where(
                InterventionOutcome.intervention_id == intervention.id,
                InterventionOutcome.metric_name
                == "assessment_average",
            )
        )

        if outcome is None:
            outcome = InterventionOutcome(
                intervention_id=intervention.id,
                metric_name="assessment_average",
                baseline_value=52,
                baseline_date=utc(2026, 10, 8),
                follow_up_value=60,
                follow_up_date=utc(2026, 10, 11),
                classification="improved",
                outcome_note=(
                    "Illustrative synthetic values: assessment "
                    "average changed from 52 to 60. This does not "
                    "establish that the intervention caused the change."
                ),
                evidence_quality="illustrative",
                recorded_at=utc(2026, 10, 11),
            )
            db.add(outcome)

        db.commit()

        print("Hero scenario seeded successfully.")
        print("Student:", student.student_code, "-", student.full_name)
        print("Assessment ID:", assessment.id)
        print("Recommendation ID:", recommendation.id)
        print("Intervention ID:", intervention.id)
        print("Intervention status:", intervention.status)
        print("Outcome evidence quality: illustrative")


if __name__ == "__main__":
    seed_hero_scenario()
