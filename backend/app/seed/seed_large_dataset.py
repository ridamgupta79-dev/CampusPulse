"""Generate a reproducible, varied synthetic CampusPulse cohort.

Run from the repository root:
    python -m app.seed.seed_large_dataset --count 2000

This command is additive and idempotent for CP-SYN-* student codes. It never
uses real student data and does not overwrite the three curated demo students.
"""
from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.init_db import create_tables
from app.db.session import SessionLocal
from app.models import Student, StudentConsent, StudentSignal

FIRST_NAMES = [
    "Aarav", "Aanya", "Aditya", "Anaya", "Arjun", "Diya", "Ishaan", "Isha",
    "Kabir", "Kiara", "Meera", "Neel", "Prisha", "Reyansh", "Riya", "Saanvi",
    "Vihaan", "Zoya", "Dev", "Myra", "Rohan", "Anika", "Kavya", "Yash",
]
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Mehta", "Patel", "Singh", "Rao", "Kumar",
    "Joshi", "Malhotra", "Das", "Kapoor", "Nair", "Shah", "Mishra", "Bose",
]
DEPARTMENTS = [
    ("Information Technology", "IT"),
    ("Computer Science", "CSE"),
    ("Electronics & Communication", "ECE"),
    ("Mechanical Engineering", "ME"),
    ("Business Administration", "MBA"),
]
PURPOSES = ("academic_support", "placement_support", "finance_support")


def build_student(index: int, rng: random.Random) -> dict:
    dept, short = rng.choice(DEPARTMENTS)
    year = rng.randint(1, 4)
    return {
        "student_code": f"CP-SYN-{index:05d}",
        "full_name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
        "program": "MBA" if short == "MBA" else "B.Tech",
        "department": dept,
        "year_of_study": year,
        "cohort": f"{short}-Year-{year}",
        "advisor_name": f"Faculty {rng.randint(1, 45):02d}",
        "mentor_name": f"Mentor {rng.randint(1, 80):02d}",
    }


def build_signals(student_id: int, rng: random.Random, now: datetime) -> list[StudentSignal]:
    # Shared latent profile creates plausible correlations rather than unrelated noise.
    profile = rng.choices(
        ["steady", "watch", "support"],
        weights=[0.58, 0.27, 0.15],
        k=1,
    )[0]
    if profile == "steady":
        attendance, marks, participation, skills = (
            rng.randint(78, 99), rng.randint(65, 96), rng.randint(55, 100), rng.randint(55, 98)
        )
    elif profile == "watch":
        attendance, marks, participation, skills = (
            rng.randint(62, 84), rng.randint(48, 76), rng.randint(30, 72), rng.randint(40, 82)
        )
    else:
        attendance, marks, participation, skills = (
            rng.randint(35, 69), rng.randint(25, 58), rng.randint(10, 48), rng.randint(25, 65)
        )

    rows = [
        ("attendance", "attendance_percentage", float(attendance), None, "academic_support"),
        ("academics", "assessment_average", float(marks), None, "academic_support"),
        ("participation", "participation_score", float(participation), None, "academic_support"),
        ("fees", "fee_support_followup_needed", None,
         rng.choice(["follow-up requested", "no follow-up recorded", "support information shared"]),
         "finance_support"),
        ("skills", "placement_readiness_score", float(skills), None, "placement_support"),
        ("faculty_feedback", "structured_support_flag", None,
         rng.choice(["check-in suggested", "progress noted", "assignment planning support"]),
         "academic_support"),
    ]
    result: list[StudentSignal] = []
    for domain, name, number, text, purpose in rows:
        quality = rng.choices(["valid", "stale", "missing"], [0.87, 0.08, 0.05], k=1)[0]
        recorded = now - timedelta(days=rng.randint(0, 110 if quality == "stale" else 25))
        if quality == "missing":
            number, text = None, None
        result.append(StudentSignal(
            student_id=student_id,
            domain=domain,
            signal_name=name,
            numeric_value=number,
            text_value=text,
            recorded_at=recorded,
            source_label="Synthetic cohort generator v1",
            quality_status=quality,
            purpose_category=purpose,
            note="Synthetic demonstration signal; not an actual student record.",
        ))
    return result


def seed_large_dataset(count: int = 2000, seed: int = 20261012) -> None:
    if count < 1:
        raise ValueError("count must be at least 1")
    create_tables()
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    inserted = 0
    with SessionLocal() as db:
        existing_codes = set(db.scalars(
            select(Student.student_code).where(Student.student_code.like("CP-SYN-%"))
        ).all())
        target_total = count
        next_index = 1
        while len(existing_codes) + inserted < target_total:
            code = f"CP-SYN-{next_index:05d}"
            next_index += 1
            if code in existing_codes:
                continue
            student_data = build_student(next_index - 1, rng)
            student_data["student_code"] = code
            student = Student(**student_data)
            db.add(student)
            db.flush()
            consents = []
            for purpose in PURPOSES:
                status = rng.choices(
                    ["granted", "unknown", "declined", "withdrawn"],
                    [0.72, 0.14, 0.10, 0.04],
                    k=1,
                )[0]
                consents.append(StudentConsent(
                    student_id=student.id,
                    purpose=purpose,
                    status=status,
                    recorded_at=now - timedelta(days=rng.randint(0, 180)),
                    source="Synthetic cohort generator",
                    note="Demo consent state only; not legal consent evidence.",
                ))
            db.add_all(consents)
            db.add_all(build_signals(student.id, rng, now))
            inserted += 1
            if inserted % 250 == 0:
                db.commit()
                print(f"Inserted {inserted}/{count} synthetic students...")
        db.commit()
    print(f"Added {inserted} synthetic students. Cohort target: {count}.")
    print("All generated records are fictional and labeled as synthetic.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261012)
    args = parser.parse_args()
    seed_large_dataset(args.count, args.seed)
