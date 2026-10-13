
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.init_db import create_tables
from app.db.session import SessionLocal
from app.models import Student, StudentConsent, StudentSignal


def utc(year: int, month: int, day: int) -> datetime:
    """Create a fixed UTC timestamp for reproducible demo data."""
    return datetime(year, month, day, tzinfo=timezone.utc)


CONSENTS = [
    ("CP-DEMO-0042", "academic_support", "granted"),
    ("CP-DEMO-0042", "counselling_referral", "unknown"),
    ("CP-DEMO-0042", "placement_support", "declined"),
    ("CP-DEMO-0043", "academic_support", "granted"),
    ("CP-DEMO-0043", "placement_support", "granted"),
    ("CP-DEMO-0044", "academic_support", "unknown"),
    ("CP-DEMO-0044", "placement_support", "withdrawn"),
]


SIGNALS = [
    # Hero student: CP-DEMO-0042
    {
        "student_code": "CP-DEMO-0042",
        "domain": "attendance",
        "signal_name": "attendance_percentage",
        "numeric_value": 78,
        "text_value": None,
        "recorded_at": utc(2026, 9, 1),
        "quality_status": "valid",
        "purpose_category": "academic_support",
        "note": "Earlier attendance observation; synthetic data.",
    },
    {
        "student_code": "CP-DEMO-0042",
        "domain": "attendance",
        "signal_name": "attendance_percentage",
        "numeric_value": 61,
        "text_value": None,
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "valid",
        "purpose_category": "academic_support",
        "note": "Recent attendance observation; synthetic data.",
    },
    {
        "student_code": "CP-DEMO-0042",
        "domain": "academics",
        "signal_name": "assessment_average",
        "numeric_value": 68,
        "text_value": None,
        "recorded_at": utc(2026, 9, 1),
        "quality_status": "valid",
        "purpose_category": "academic_support",
        "note": "Earlier assessment average; synthetic data.",
    },
    {
        "student_code": "CP-DEMO-0042",
        "domain": "academics",
        "signal_name": "assessment_average",
        "numeric_value": 52,
        "text_value": None,
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "valid",
        "purpose_category": "academic_support",
        "note": "Recent assessment average; synthetic data.",
    },
    {
        "student_code": "CP-DEMO-0042",
        "domain": "academics",
        "signal_name": "assignments_completed",
        "numeric_value": 5,
        "text_value": "5 of 8 assignments completed",
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "valid",
        "purpose_category": "academic_support",
        "note": "Synthetic assignment progress.",
    },
    {
        "student_code": "CP-DEMO-0042",
        "domain": "participation",
        "signal_name": "participation_activity",
        "numeric_value": None,
        "text_value": None,
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "missing",
        "purpose_category": "academic_support",
        "note": "No usable participation record. Do not infer disengagement.",
    },
    {
        "student_code": "CP-DEMO-0042",
        "domain": "fees",
        "signal_name": "financial_support_followup",
        "numeric_value": None,
        "text_value": "Restricted demo follow-up indicator",
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "valid",
        "purpose_category": "finance_support",
        "note": "Synthetic restricted signal; not for general display.",
    },
    {
        "student_code": "CP-DEMO-0042",
        "domain": "skills",
        "signal_name": "python_skill_assessment",
        "numeric_value": 72,
        "text_value": None,
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "valid",
        "purpose_category": "placement_support",
        "note": "Synthetic skills observation.",
    },
    {
        "student_code": "CP-DEMO-0042",
        "domain": "faculty_feedback",
        "signal_name": "pending_lab_submissions",
        "numeric_value": 2,
        "text_value": "Two lab submissions are pending",
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "valid",
        "purpose_category": "academic_support",
        "note": "Structured synthetic faculty observation.",
    },

    # Second student: valid and stale observations
    {
        "student_code": "CP-DEMO-0043",
        "domain": "attendance",
        "signal_name": "attendance_percentage",
        "numeric_value": 84,
        "text_value": None,
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "valid",
        "purpose_category": "academic_support",
        "note": "Synthetic attendance observation.",
    },
    {
        "student_code": "CP-DEMO-0043",
        "domain": "academics",
        "signal_name": "assessment_average",
        "numeric_value": 74,
        "text_value": None,
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "valid",
        "purpose_category": "academic_support",
        "note": "Synthetic assessment observation.",
    },
    {
        "student_code": "CP-DEMO-0043",
        "domain": "participation",
        "signal_name": "participation_activity",
        "numeric_value": 3,
        "text_value": "Three recorded activities",
        "recorded_at": utc(2026, 7, 1),
        "quality_status": "stale",
        "purpose_category": "academic_support",
        "note": "Old observation; confirm before relying on it.",
    },
    {
        "student_code": "CP-DEMO-0043",
        "domain": "fees",
        "signal_name": "financial_support_followup",
        "numeric_value": None,
        "text_value": "No detailed finance data seeded",
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "missing",
        "purpose_category": "finance_support",
        "note": "Absence of data is not evidence of a financial problem.",
    },
    {
        "student_code": "CP-DEMO-0043",
        "domain": "skills",
        "signal_name": "python_skill_assessment",
        "numeric_value": 81,
        "text_value": None,
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "valid",
        "purpose_category": "placement_support",
        "note": "Synthetic skills observation.",
    },
    {
        "student_code": "CP-DEMO-0043",
        "domain": "faculty_feedback",
        "signal_name": "faculty_observation",
        "numeric_value": None,
        "text_value": "No recent structured observation",
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "missing",
        "purpose_category": "academic_support",
        "note": "No usable faculty-feedback observation.",
    },

    # Third student: varied signals and unknown participation
    {
        "student_code": "CP-DEMO-0044",
        "domain": "attendance",
        "signal_name": "attendance_percentage",
        "numeric_value": 91,
        "text_value": None,
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "valid",
        "purpose_category": "academic_support",
        "note": "Synthetic attendance observation.",
    },
    {
        "student_code": "CP-DEMO-0044",
        "domain": "academics",
        "signal_name": "assessment_average",
        "numeric_value": 63,
        "text_value": None,
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "valid",
        "purpose_category": "academic_support",
        "note": "Synthetic assessment observation.",
    },
    {
        "student_code": "CP-DEMO-0044",
        "domain": "participation",
        "signal_name": "participation_activity",
        "numeric_value": None,
        "text_value": None,
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "missing",
        "purpose_category": "academic_support",
        "note": "No participation data available.",
    },
    {
        "student_code": "CP-DEMO-0044",
        "domain": "fees",
        "signal_name": "financial_support_followup",
        "numeric_value": None,
        "text_value": "No detailed finance data seeded",
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "missing",
        "purpose_category": "finance_support",
        "note": "No finance information available in this demo.",
    },
    {
        "student_code": "CP-DEMO-0044",
        "domain": "skills",
        "signal_name": "python_skill_assessment",
        "numeric_value": 58,
        "text_value": None,
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "valid",
        "purpose_category": "placement_support",
        "note": "Synthetic skills observation.",
    },
    {
        "student_code": "CP-DEMO-0044",
        "domain": "faculty_feedback",
        "signal_name": "faculty_observation",
        "numeric_value": None,
        "text_value": "Follow-up context not yet recorded",
        "recorded_at": utc(2026, 10, 8),
        "quality_status": "valid",
        "purpose_category": "academic_support",
        "note": "Synthetic faculty context awaiting review.",
    },
]


def seed_context() -> None:
    """Insert missing consent and signal records without duplicates."""
    create_tables()
    inserted_consents = 0
    inserted_signals = 0

    with SessionLocal() as db:
        students = {
            student.student_code: student.id
            for student in db.scalars(select(Student)).all()
        }

        required_codes = {code for code, _, _ in CONSENTS}
        required_codes.update(signal["student_code"] for signal in SIGNALS)
        missing_codes = required_codes - students.keys()

        if missing_codes:
            raise RuntimeError(
                "Seed students first. Missing student codes: "
                + ", ".join(sorted(missing_codes))
            )

        for student_code, purpose, status in CONSENTS:
            student_id = students[student_code]
            existing = db.scalar(
                select(StudentConsent).where(
                    StudentConsent.student_id == student_id,
                    StudentConsent.purpose == purpose,
                )
            )
            if existing is None:
                db.add(
                    StudentConsent(
                        student_id=student_id,
                        purpose=purpose,
                        status=status,
                        source="synthetic_demo",
                        note="Illustrative consent state; not real consent.",
                    )
                )
                inserted_consents += 1

        for item in SIGNALS:
            student_id = students[item["student_code"]]
            existing = db.scalar(
                select(StudentSignal).where(
                    StudentSignal.student_id == student_id,
                    StudentSignal.domain == item["domain"],
                    StudentSignal.signal_name == item["signal_name"],
                    StudentSignal.recorded_at == item["recorded_at"],
                )
            )
            if existing is None:
                values = {
                    key: value
                    for key, value in item.items()
                    if key != "student_code"
                }
                db.add(StudentSignal(student_id=student_id, **values))
                inserted_signals += 1

        db.commit()

    print(f"New consent records inserted: {inserted_consents}")
    print(f"New signal records inserted: {inserted_signals}")


if __name__ == "__main__":
    seed_context()
