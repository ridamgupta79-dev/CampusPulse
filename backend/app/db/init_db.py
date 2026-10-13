
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401


def create_tables() -> None:
    """Create any missing CampusPulse tables."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_tables()
    print("CampusPulse database tables are ready.")
    print("Tables:", sorted(Base.metadata.tables.keys()))
