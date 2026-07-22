"""
Regression coverage for redirecting a customer straight to their library
the moment payment is confirmed — no intermediate /welcome page, no
waiting on email. Covers both payment paths: the polling flow
(/api/payments/verify, used by Bank Transfer) and the redirect flow
(/api/payments/callback, used by Pay with Bank).

The core assertion throughout: the token handed back is the real,
durable library_access_token on the user record — the exact same value
the welcome email itself links to — not the short-lived session JWT.
"""
import pytest
from unittest.mock import AsyncMock

from backend.routes import payments as payments_module


@pytest.mark.asyncio
async def test_verify_already_claimed_path_returns_real_library_token(client, test_db, monkeypatch):
    """Covers the 'someone already confirmed this payment' branch — e.g.
    the webhook won the race before the poll request landed."""
    monkeypatch.setattr(payments_module, "send_email", AsyncMock(return_value=(True, None)))

    email = "already-claimed@example.com"
    user_id = (await test_db.users.insert_one({
        "name": "Already Claimed", "email": email, "role": "customer",
        "is_active": True, "purchased_products": ["all"],
        "library_access_token": "real-durable-token-abc123",
    })).inserted_id
    await test_db.subscribers.insert_one({"email": email, "name": "Already Claimed", "is_active": True})
    await test_db.payments.insert_one({"reference": "ACP-ALREADY1", "status": "success", "amount": 2000})

    res = await client.post("/api/payments/verify", json={
        "reference": "ACP-ALREADY1", "email": email, "name": "Already Claimed",
        "payment_method": "bank_transfer",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["library_token"] == "real-durable-token-abc123"
    # The JWT session token must never be confused with the durable one.
    assert data["token"] != data["library_token"]


@pytest.mark.asyncio
async def test_verify_fresh_completion_returns_real_library_token(client, test_db, monkeypatch):
    """Covers a brand-new completion via the polling path (Bank Transfer)."""
    monkeypatch.setattr(payments_module, "send_email", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr(
        payments_module, "verify_transaction",
        AsyncMock(return_value={
            "status": True,
            "data": {"status": "success", "amount": 200000, "id": 999888},
        }),
    )

    res = await client.post("/api/payments/verify", json={
        "reference": "ACP-FRESH0001", "email": "fresh-poll@example.com", "name": "Fresh Poller",
        "payment_method": "bank_transfer",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["library_token"]

    user = await test_db.users.find_one({"email": "fresh-poll@example.com"})
    assert user["library_access_token"] == data["library_token"]

    # The welcome email queued for this customer must carry the exact
    # same durable token — the immediate redirect and the email are two
    # doors to the same room, never two different tokens.
    queued = await test_db.email_queue.find_one({"email": "fresh-poll@example.com", "kind": "welcome"})
    assert queued is not None
    assert queued["access_token"] == data["library_token"]


@pytest.mark.asyncio
async def test_callback_redirects_straight_to_library_not_welcome(client, test_db, monkeypatch):
    """Covers the redirect-based flow (Pay with Bank / card) — Paystack's
    own callback_url hit after the customer completes payment there."""
    monkeypatch.setattr(payments_module, "send_email", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr(
        payments_module, "verify_transaction",
        AsyncMock(return_value={
            "status": True,
            "data": {"status": "success", "amount": 200000, "id": 777666},
        }),
    )

    await test_db.pending_payments.insert_one({
        "reference": "ACP-CALLBACK01",
        "email": "callback-customer@example.com",
        "name": "Callback Customer",
        "payment_method": "pay_with_bank",
    })

    res = await client.get(
        "/api/payments/callback?reference=ACP-CALLBACK01",
        follow_redirects=False,
    )
    assert res.status_code in (302, 307)
    location = res.headers["location"]
    assert location.startswith("/library?token=")
    assert "welcome=1" in location
    assert "/welcome" not in location

    user = await test_db.users.find_one({"email": "callback-customer@example.com"})
    assert user["library_access_token"] in location


@pytest.mark.asyncio
async def test_welcome_route_gracefully_redirects_to_library(client):
    """Anyone with an old /welcome?token=... tab or bookmark still open
    should land somewhere useful, not hit a dead page."""
    res = await client.get("/welcome?token=some-old-token", follow_redirects=False)
    assert res.status_code in (302, 307)
    location = res.headers["location"]
    assert location.startswith("/library?token=some-old-token")
