"""Shared test setup: an isolated database and authenticated API helpers.

Every test run points CampusPulse at a throwaway SQLite file via
CAMPUSPULSE_DATABASE_URL, so the supplied backend/data/campuspulse.db is
never touched. The curated demo students, signals, consents, hero workflow,
and demo accounts are seeded into that throwaway database so existing tests
keep exercising the same scenarios.
"""
import os
import pathlib
import shutil
import tempfile

_TMP_DIR = pathlib.Path(tempfile.mkdtemp(prefix="campuspulse-tests-"))
_TEST_DB = _TMP_DIR / "campuspulse-test.db"

# Must be configured before any app.db.session import binds the engine.
os.environ.setdefault(
    "CAMPUSPULSE_DATABASE_URL",
    f"sqlite:///{_TEST_DB.as_posix()}",
)
os.environ.setdefault(
    "AUTH_JWT_SECRET",
    "test-only-signing-secret-0123456789abcdef0123456789abcdef",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.routes.auth import DEMO_PASSWORD, seed_demo_users  # noqa: E402
from app.db.init_db import create_tables  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.seed.seed_context import seed_context  # noqa: E402
from app.seed.seed_hero_scenario import seed_hero_scenario  # noqa: E402
from app.seed.seed_intervention_states import seed_intervention_states  # noqa: E402
from app.seed.seed_reward_catalogue import seed_reward_catalogue  # noqa: E402
from app.seed.seed_students import seed_students  # noqa: E402

# Prepare the isolated database before any module-level TestClient login.
create_tables()
with SessionLocal() as db:
    seed_demo_users(db)
    seed_reward_catalogue(db)

client = TestClient(app)


def auth_headers(role: str) -> dict[str, str]:
    """Sign in as the demo account for ``role`` and return bearer headers."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": f"{role}@campuspulse.demo",
            "password": DEMO_PASSWORD,
            "role": role,
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="session", autouse=True)
def seeded_demo_workflow_data():
    """Seed the curated demo workflow once for the whole test session."""
    seed_students()
    seed_context()
    seed_hero_scenario()
    seed_intervention_states()
    yield
    shutil.rmtree(_TMP_DIR, ignore_errors=True)
