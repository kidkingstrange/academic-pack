"""
Regression coverage for Paystack webhook signature verification and payload handling.
"""
import hashlib
import hmac
import json

import pytest
from unittest.mock import AsyncMock

from backend.config import get_settings

settings = get_settings()
WEBHOOK_URL = "/api/payments/webhook"


def _sign(raw_body: bytes) -> str:
    secret = (settings.PAYSTACK_SECRET_KEY or "").strip()
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()


def _payload(ref: str, email: str = "customer@example.com", amount_naira: float = 2000):
    return {
        "event": "charge.success",
        "data": {
            "status": "success",
            "reference": ref,
            "id": 123456,
            "amount": int(amount_naira * 100),
            "customer": {"email": email, "first_name": "Test", "last_name": "Customer"},
        },
    }


@pytest.mark.asyncio
async def test_webhook_rejects_missing_signature(client):
    body = _payload("ACP-NOSIG-001")
    res = await client.post(WEBHOOK_URL, json=body)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_webhook_rejects_mismatched_signature(client):
    body = _payload("ACP-BADSIG-001")
    res = await client.post(
        WEBHOOK_URL,
        content=json.dumps(body),
        headers={
            "Content-Type": "application/json",
            "x-paystack-signature": "not-the-real-signature",
        },
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_webhook_accepts_correct_hmac_signature(client, test_db, monkeypatch):
    monkeypatch.setattr("backend.routes.payments.send_email", AsyncMock(return_value=(True, None)))
    body = _payload("ACP-GOODSIG-001")
    raw = json.dumps(body).encode("utf-8")
    res = await client.post(
        WEBHOOK_URL,
        content=raw,
        headers={
            "Content-Type": "application/json",
            "x-paystack-signature": _sign(raw),
        },
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_webhook_flags_unmatched_reference_instead_of_trusting_payload(client, test_db, monkeypatch):
    mock_send = AsyncMock(return_value=(True, None))
    monkeypatch.setattr("backend.routes.payments.send_email", mock_send)

    ref = "ACP-ORPHAN-001"
    body = _payload(ref, email="attacker-controlled@example.com", amount_naira=999999)
    raw = json.dumps(body).encode("utf-8")
    res = await client.post(
        WEBHOOK_URL,
        content=raw,
        headers={
            "Content-Type": "application/json",
            "x-paystack-signature": _sign(raw),
        },
    )
    assert res.status_code == 200

    flagged = await test_db.flagged_payments.find_one({"reference": ref})
    assert flagged is not None
    assert flagged["reason"] == "no_matching_pending_payment"

    user = await test_db.users.find_one({"email": "attacker-controlled@example.com"})
    assert user is None, "No user/access should be granted for an unmatched reference"

    mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_webhook_completes_payment_with_matching_pending_record(client, test_db, monkeypatch):
    monkeypatch.setattr("backend.services.payment_completion.process_email_queue", AsyncMock())

    ref = "ACP-REALFLOW-001"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "email": "realcustomer@example.com",
        "name": "Real Customer",
        "amount": 2000,
        "charge_id": "PAYSTACK-CHG-REAL",
        "payment_method": "bank_transfer",
    })

    body = _payload(ref, email="realcustomer@example.com", amount_naira=2000)
    raw = json.dumps(body).encode("utf-8")
    res = await client.post(
        WEBHOOK_URL,
        content=raw,
        headers={
            "Content-Type": "application/json",
            "x-paystack-signature": _sign(raw),
        },
    )
    assert res.status_code == 200

    user = await test_db.users.find_one({"email": "realcustomer@example.com"})
    assert user is not None
    assert user["library_access_token"]

    payment = await test_db.payments.find_one({"reference": ref})
    assert payment is not None
    assert payment["status"] == "success"
