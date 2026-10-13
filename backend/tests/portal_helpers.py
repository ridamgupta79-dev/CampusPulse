"""Shared helpers for student-portal tests."""
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Student, StudentAccountLink
from app.models.auth_user import AuthUser


def get_student_by_code(code: str) -> Student:
    with SessionLocal() as db:
        student = db.scalar(
            select(Student).where(Student.student_code == code)
        )
        assert student is not None
        return student


def get_user_by_email(email: str) -> AuthUser:
    with SessionLocal() as db:
        user = db.scalar(select(AuthUser).where(AuthUser.email == email))
        assert user is not None
        return user


def register_account(client, email: str, role: str = "student") -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "SecurePass123",
            "full_name": "Portal Test Student",
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_headers(client, email: str, role: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": "SecurePass123",
            "role": role,
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def link_account_directly(email: str, student_code: str) -> None:
    """Bind an account to a record the way enrollment would."""
    with SessionLocal() as db:
        user = db.scalar(select(AuthUser).where(AuthUser.email == email))
        student = db.scalar(
            select(Student).where(Student.student_code == student_code)
        )
        assert user is not None and student is not None
        if (
            db.query(StudentAccountLink)
            .filter(StudentAccountLink.user_id == user.id)
            .first()
            is None
        ):
            db.add(StudentAccountLink(user_id=user.id, student_id=student.id))
            db.commit()


def create_student_record(code: str, name: str, cohort: str) -> None:
    with SessionLocal() as db:
        if (
            db.scalar(select(Student).where(Student.student_code == code))
            is None
        ):
            db.add(Student(
                student_code=code,
                full_name=name,
                program="B.Tech",
                department="Information Technology",
                year_of_study=2,
                cohort=cohort,
            ))
            db.commit()
