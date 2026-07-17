"""
Regression coverage for the Flutterwave webhook signature bypass (audit
Critical #1/#2): backend/routes/payments.py previously logged a warning on
a missing/mismatched signature but processed the event anyway, and trusted
payload-supplied email/amount when no matching pending_payments record
existed.
"""
import base64
import hashlib
import hmac
import json

import pytest
from unittest.mock import AsyncMock

from backend.config import get_settings

settings = get_settings()
WEBHOOK_URL = "/api/payments/webhook"


def _sign(raw_body: bytes) -> str:
    secret = settings.FLW_WEBHOOK_SECRET_HASH.strip()
    return base64.b64encode(hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()).decode()


def _payload(ref: str, email: str = "customer@example.com", amount: float = 2000):
    return {
        "type": "charge.completed",
        "data": {
            "status": "succeeded",
            "tx_ref": ref,
            "id": "FLW-CHG-123",
            "amount": amount,
            "customer": {"email": email, "name": "Test Customer"},
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
            "flutterwave-signature": "not-the-real-signature",
        },
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_webhook_rejects_wrong_verif_hash(client):
    body = _payload("ACP-BADHASH-001")
    res = await client.post(
        WEBHOOK_URL,
        json=body,
        headers={"verif-hash": "totally-wrong-hash"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_webhook_accepts_correct_verif_hash(client, test_db, monkeypatch):
    monkeypatch.setattr("backend.routes.payments.send_email", AsyncMock(return_value=(True, None)))
    body = _payload("ACP-GOODHASH-001")
    res = await client.post(
        WEBHOOK_URL,
        json=body,
        headers={"verif-hash": settings.FLW_WEBHOOK_SECRET_HASH},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_webhook_accepts_correct_hmac_signature(client, test_db, monkeypatch):
    monkeypatch.setattr("backend.routes.payments.send_email", AsyncMock(return_value=(True, None)))
    body = _payload("ACP-GOODSIG-001")
    raw = json.dumps(body).encode()
    res = await client.post(
        WEBHOOK_URL,
        content=raw,
        headers={
            "Content-Type": "application/json",
            "flutterwave-signature": _sign(raw),
        },
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_webhook_flags_unmatched_reference_instead_of_trusting_payload(client, test_db, monkeypatch):
    """No pending_payments record exists for this ACP- reference. Even with
    a valid signature, the payload's claimed email/amount must not be
    trusted to grant access — it should be flagged for manual review."""
    mock_send = AsyncMock(return_value=(True, None))
    monkeypatch.setattr("backend.routes.payments.send_email", mock_send)

    ref = "ACP-ORPHAN-001"
    body = _payload(ref, email="attacker-controlled@example.com", amount=999999)
    res = await client.post(
        WEBHOOK_URL,
        json=body,
        headers={"verif-hash": settings.FLW_WEBHOOK_SECRET_HASH},
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
    """A real checkout flow: a pending_payments record already exists for
    this reference, so a verified webhook should complete it normally."""
    monkeypatch.setattr("backend.services.payment_completion.process_email_queue", AsyncMock())

    ref = "ACP-REALFLOW-001"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "email": "realcustomer@example.com",
        "name": "Real Customer",
        "amount": 2000,
        "charge_id": "FLW-CHG-REAL",
        "payment_method": "bank_transfer",
    })

    body = _payload(ref, email="realcustomer@example.com", amount=2000)
    res = await client.post(
        WEBHOOK_URL,
        json=body,
        headers={"verif-hash": settings.FLW_WEBHOOK_SECRET_HASH},
    )
    assert res.status_code == 200

    user = await test_db.users.find_one({"email": "realcustomer@example.com"})
    assert user is not None
    assert user["library_access_token"]

    payment = await test_db.payments.find_one({"reference": ref})
    assert payment is not None
    assert payment["status"] == "success"
