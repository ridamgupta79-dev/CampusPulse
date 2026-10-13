"""Marketplace: leaderboard derivation, redemption rules, persistence.

Each test provisions its own linked student so balance assertions never
depend on execution order within the module.
"""
from sqlalchemy import select

from conftest import client
from portal_helpers import (
    create_student_record,
    link_account_directly,
    login_headers,
    register_account,
)

from app.db.session import SessionLocal
from app.models import Reward, Student
from app.services.pulse_points import _append_ledger_and_update_account

MARKET_STUDENT = "CP-TEST-MKT-1"
MARKET_EMAIL = "market.student@example.com"
MARKET_COHORT = "IT-Year-2"
TIE_COHORT = "MKT-Tie-Cohort"


def setup_module(module):
    create_student_record(MARKET_STUDENT, "Market Student", MARKET_COHORT)
    register_account(client, MARKET_EMAIL)
    link_account_directly(MARKET_EMAIL, MARKET_STUDENT)


def _make_student(suffix: str, name: str, cohort: str) -> str:
    code = f"CP-TEST-MKT-{suffix}"
    email = f"market.{suffix}@example.com"
    create_student_record(code, name, cohort)
    register_account(client, email)
    link_account_directly(email, code)
    return email


def _grant(points: int, key: str, student_code: str = MARKET_STUDENT) -> None:
    with SessionLocal() as db:
        student_id = db.scalar(
            select(Student.id).where(Student.student_code == student_code)
        )
        entry = _append_ledger_and_update_account(
            db,
            student_id=student_id,
            txn_type="award",
            amount=points,
            idempotency_key=key,
            reason="Marketplace test award",
        )
        db.commit()
        assert entry is not None


def test_rewards_catalogue_is_backend_controlled():
    email = _make_student("cat", "Catalogue Student", MARKET_COHORT)
    _grant(30, "test:mkt:cat:1", "CP-TEST-MKT-cat")
    response = client.get(
        "/api/student/marketplace/rewards",
        headers=login_headers(client, email, "student"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == 30
    rewards = body["rewards"]
    assert len(rewards) >= 9
    badge = next(r for r in rewards if r["cost"] == 25)
    assert badge["affordable"] is True
    premium = next(r for r in rewards if r["cost"] == 750)
    assert premium["affordable"] is False
    assert premium["points_needed"] == 720
    # Simulated vouchers are clearly labelled.
    simulated = [r for r in rewards if r["reward_type"] == "simulated"]
    assert simulated and all(
        "simulated" in (r["name"] + r["description"]).lower()
        for r in simulated
    )


def test_leaderboard_ranks_from_ledger_with_ties_and_pagination():
    # A dedicated cohort keeps the ranking hermetic from other test modules;
    # 200 net points outranks anything else the suite can create.
    email1 = _make_student("tie1", "Tie Alpha", TIE_COHORT)
    email2 = _make_student("tie2", "Tie Beta", TIE_COHORT)
    _grant(200, "test:mkt:tie:1", "CP-TEST-MKT-tie1")
    _grant(200, "test:mkt:tie:2", "CP-TEST-MKT-tie2")

    headers = login_headers(client, email1, "student")
    response = client.get(
        f"/api/student/marketplace/leaderboard?cohort={TIE_COHORT}"
        "&page=1&page_size=5",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["entries"]) == 2

    # The two tied students share rank 1; ordering is deterministic.
    top = body["entries"]
    assert top[0]["net_earned"] == 200 and top[1]["net_earned"] == 200
    assert top[0]["rank"] == 1 and top[1]["rank"] == 1
    assert [e["display_name"] for e in top] == [
        e["display_name"] for e in sorted(top, key=lambda e: e["display_name"])
    ]
    assert body["me"]["rank"] == 1
    for item in body["entries"]:
        assert "email" not in item

    # Rankings update after a legitimate award.
    _grant(10, "test:mkt:tie:3", "CP-TEST-MKT-tie1")
    response = client.get(
        f"/api/student/marketplace/leaderboard?cohort={TIE_COHORT}",
        headers=headers,
    )
    body = response.json()
    assert body["me"]["rank"] == 1
    assert body["me"]["net_earned"] == 210
    assert body["entries"][0]["is_current_student"] is True
    assert body["entries"][0]["net_earned"] == 210
    # The other tie student's net is unchanged.
    assert body["entries"][1]["net_earned"] == 200

    # Unused account stays signed out of the ranking results entirely.
    assert email2  # tie2 is linked; both entries shown above are cohort-only.


def test_redemption_success_flow_and_persistence():
    email = _make_student("redeem", "Redeem Student", MARKET_COHORT)
    _grant(25, "test:mkt:redeem:1", "CP-TEST-MKT-redeem")
    headers = login_headers(client, email, "student")

    rewards = client.get(
        "/api/student/marketplace/rewards", headers=headers
    ).json()["rewards"]
    badge = next(r for r in rewards if r["cost"] == 25)

    redeem = client.post(
        "/api/student/marketplace/redeem",
        json={"reward_id": badge["id"]},
        headers=headers,
    )
    assert redeem.status_code == 200, redeem.text
    body = redeem.json()
    assert body["reference"].startswith("CP-RED-")
    assert body["balance_after"] == 0

    balance = client.get("/api/student/pulse/balance", headers=headers)
    assert balance.json()["balance"] == 0

    history = client.get(
        "/api/student/marketplace/redemptions", headers=headers
    )
    assert history.status_code == 200
    matches = [
        h for h in history.json() if h["reference"] == body["reference"]
    ]
    assert len(matches) == 1

    # A second redemption of the same reward is rejected.
    again = client.post(
        "/api/student/marketplace/redeem",
        json={"reward_id": badge["id"]},
        headers=headers,
    )
    assert again.status_code == 409

    # History still shows exactly one record.
    history = client.get(
        "/api/student/marketplace/redemptions", headers=headers
    )
    matches = [
        h
        for h in history.json()
        if h["reference"] == body["reference"]
    ]
    assert len(matches) == 1


def test_insufficient_points_prevent_redemption():
    email = _make_student("insufficient", "Insufficient Student", MARKET_COHORT)
    _grant(5, "test:mkt:insufficient:1", "CP-TEST-MKT-insufficient")
    headers = login_headers(client, email, "student")
    rewards = client.get(
        "/api/student/marketplace/rewards", headers=headers
    ).json()["rewards"]
    expensive = next(r for r in rewards if r["cost"] == 750)

    response = client.post(
        "/api/student/marketplace/redeem",
        json={"reward_id": expensive["id"]},
        headers=headers,
    )
    assert response.status_code == 409
    assert "insufficient" in response.json()["detail"].lower()

    balance = client.get("/api/student/pulse/balance", headers=headers)
    assert balance.json()["balance"] == 5


def test_out_of_stock_rewards_cannot_be_redeemed():
    with SessionLocal() as db:
        reward = db.scalar(
            select(Reward).where(Reward.sku == "CP-RWD-BOOK-500")
        )
        reward.stock = 0
        db.commit()
        reward_id = reward.id

    _grant(600, "test:mkt:stock:1")
    response = client.post(
        "/api/student/marketplace/redeem",
        json={"reward_id": reward_id},
        headers=login_headers(client, MARKET_EMAIL, "student"),
    )
    assert response.status_code == 409
    assert "stock" in response.json()["detail"].lower()


def test_unknown_or_inactive_reward_is_rejected():
    response = client.post(
        "/api/student/marketplace/redeem",
        json={"reward_id": 999999},
        headers=login_headers(client, MARKET_EMAIL, "student"),
    )
    assert response.status_code == 404
