
from sqlalchemy import select

from app.db.init_db import create_tables
from app.db.session import SessionLocal
from app.models import Student


SYNTHETIC_STUDENTS = [
    {
        "student_code": "CP-DEMO-0042",
        "full_name": "Aarav Mehta",
        "program": "B.Tech",
        "department": "Information Technology",
        "year_of_study": 2,
        "cohort": "IT-Year-2",
        "advisor_name": "Faculty Demo 01",
        "mentor_name": "Mentor Demo 01",
    },
    {
        "student_code": "CP-DEMO-0043",
        "full_name": "Diya Sharma",
        "program": "B.Tech",
        "department": "Information Technology",
        "year_of_study": 2,
        "cohort": "IT-Year-2",
        "advisor_name": "Faculty Demo 01",
        "mentor_name": "Mentor Demo 02",
    },
    {
        "student_code": "CP-DEMO-0044",
        "full_name": "Kabir Verma",
        "program": "B.Tech",
        "department": "Information Technology",
        "year_of_study": 2,
        "cohort": "IT-Year-2",
        "advisor_name": None,
        "mentor_name": "Mentor Demo 02",
    },
]


def seed_students() -> None:
    """Insert missing synthetic students without duplicating existing records."""
    create_tables()

    inserted = 0
    existing = 0

    with SessionLocal() as db:
        for student_data in SYNTHETIC_STUDENTS:
            statement = select(Student).where(
                Student.student_code == student_data["student_code"]
            )
            student = db.scalar(statement)

            if student is not None:
                existing += 1
                continue

            db.add(Student(**student_data))
            inserted += 1

        db.commit()

    print(f"New students inserted: {inserted}")
    print(f"Students already present: {existing}")


if __name__ == "__main__":
    seed_students()
