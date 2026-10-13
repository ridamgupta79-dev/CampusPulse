
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.init_db import create_tables
from app.db.session import SessionLocal
from app.models import Intervention, Student


def seed_intervention_states() -> None:
    create_tables()
    db = SessionLocal()

    try:
        student = db.scalar(
            select(Student).where(
                Student.student_code == "CP-DEMO-0044"
            )
        )

        if student is None:
            raise RuntimeError(
                "CP-DEMO-0044 is missing. Run the student seed first."
            )

        existing = db.scalar(
            select(Intervention).where(
                Intervention.student_id == student.id,
                Intervention.intervention_type == "placement_readiness",
            )
        )

        if existing is not None:
            print(
                "Placement-readiness intervention already exists:",
                existing.id,
            )
            return

        intervention = Intervention(
            student_id=student.id,
            recommendation_id=None,
            intervention_type="placement_readiness",
            description=(
                "Offer a human-reviewed skills and placement-readiness "
                "check-in. This is supportive, not a judgment of ability."
            ),
            assigned_role="placement",
            assigned_owner="Placement Demo 01",
            supporting_role="mentor",
            due_date=datetime(2026, 10, 10, tzinfo=timezone.utc),
            status="assigned",
            priority="normal",
            override_reason=None,
            created_at=datetime(2026, 10, 8, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 8, tzinfo=timezone.utc),
        )

        db.add(intervention)
        db.commit()

        print("Created placement-readiness intervention:", intervention.id)
        print("Student:", student.student_code)
        print("Status:", intervention.status)
        print("Due date:", intervention.due_date)

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_intervention_states()
