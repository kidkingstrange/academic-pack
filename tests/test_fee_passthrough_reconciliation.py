"""
Tests for Paystack fee pass-through handling, amount validation tolerance,
and automated/manual payment reconciliation.
"""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone
import json
import hmac
import hashlib

from backend.config import get_settings
from backend.services.payment_completion import is_valid_paid_amount
from backend.routes.payments import process_webhook_payment
from backend.utils.security import create_access_token

settings = get_settings()
WEBHOOK_URL = "/api/payments/webhook"


def _sign(raw_body: bytes) -> str:
    secret = (settings.PAYSTACK_SECRET_KEY or "").strip()
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()


# ── Unit Tests: is_valid_paid_amount ─────────────────────────────────────────

def test_is_valid_paid_amount_exact_match():
    assert is_valid_paid_amount(5000.0, 5000.0) is True
    assert is_valid_paid_amount(2000.0, 2000.0) is True
    assert is_valid_paid_amount(15.0, 15.0) is True


def test_is_valid_paid_amount_rounding_tolerance():
    # Within ₦1.0 tolerance
    assert is_valid_paid_amount(4999.50, 5000.0) is True
    assert is_valid_paid_amount(5000.50, 5000.0) is True
    assert is_valid_paid_amount(4998.90, 5000.0) is False


def test_is_valid_paid_amount_with_fee_deduction():
    # Customer paid ₦5,177.67, fee was ₦177.67, expected ₦5,000.00
    assert is_valid_paid_amount(5177.67, 5000.0, fee_paid=177.67) is True
    # Fee not passed explicitly, but amount is within reasonable gateway surcharge
    assert is_valid_paid_amount(5177.67, 5000.0, fee_paid=0.0) is True


def test_is_valid_paid_amount_strictly_rejects_underpayment():
    # Attacker tries to pay ₦1,000 or ₦100 for ₦5,000 order
    assert is_valid_paid_amount(1000.0, 5000.0) is False
    assert is_valid_paid_amount(100.0, 2000.0) is False
    assert is_valid_paid_amount(2000.0, 12500.0) is False
    assert is_valid_paid_amount(0.0, 5000.0) is False


def test_is_valid_paid_amount_rejects_bizarre_excess():
    # Absurd amount
    assert is_valid_paid_amount(500000.0, 2000.0) is False


# ── Integration Tests: Webhook & Polling with Fee Pass-Through ────────────────

@pytest.mark.asyncio
async def test_webhook_completes_when_customer_bears_paystack_fees(client, test_db, monkeypatch):
    """
    Real-world scenario where Paystack charges customer gateway fees:
    Expected order: ₦5,000.
    Paystack reports: ₦5,177.67 (517767 kobo) with fees=17767 kobo.
    Webhook must NOT flag as amount_mismatch, but successfully fulfill order.
    """
    monkeypatch.setattr("backend.services.payment_completion.process_email_queue", AsyncMock())

    ref = "ACP-FEE-TEST-001"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "email": "fee.customer@example.com",
        "name": "Fee Paying Customer",
        "amount": 5000.0,
        "base_price": 5000.0,
        "currency": "NGN",
    })

    webhook_payload = {
        "event": "charge.success",
        "data": {
            "status": "success",
            "reference": ref,
            "id": 998877,
            "amount": 517767,  # ₦5,177.67
            "fees": 17767,      # ₦177.67
            "customer": {"email": "fee.customer@example.com", "first_name": "Fee", "last_name": "Customer"},
        },
    }
    raw = json.dumps(webhook_payload).encode("utf-8")
    res = await client.post(
        WEBHOOK_URL,
        content=raw,
        headers={
            "Content-Type": "application/json",
            "x-paystack-signature": _sign(raw),
        },
    )
    assert res.status_code == 200

    # Must NOT be in flagged_payments
    flagged = await test_db.flagged_payments.find_one({"reference": ref})
    assert flagged is None, "Legitimate fee pass-through transaction must not be flagged"

    # User MUST be created with access token
    user = await test_db.users.find_one({"email": "fee.customer@example.com"})
    assert user is not None
    assert user["library_access_token"] is not None

    # Payment recorded in db.payments
    payment = await test_db.payments.find_one({"reference": ref})
    assert payment is not None
    assert payment["status"] == "success"
    assert payment["base_price"] == 5000.0


@pytest.mark.asyncio
async def test_verify_polling_accepts_fee_passthrough(client, test_db, monkeypatch):
    """
    Frontend /api/payments/verify polling endpoint must also accept fee pass-through.
    """
    monkeypatch.setattr("backend.services.payment_completion.process_email_queue", AsyncMock())

    ref = "ACP-POLL-FEE-001"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "email": "poll.customer@example.com",
        "name": "Poll Customer",
        "amount": 5000.0,
        "base_price": 5000.0,
        "currency": "NGN",
    })

    mock_verify = AsyncMock(return_value={
        "status": True,
        "data": {
            "status": "success",
            "reference": ref,
            "id": 123456,
            "amount": 517767,  # ₦5,177.67
            "fees": 17767,
        }
    })
    monkeypatch.setattr("backend.routes.payments.verify_transaction", mock_verify)

    res = await client.post("/api/payments/verify", json={
        "reference": ref,
        "email": "poll.customer@example.com",
        "name": "Poll Customer",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["token"] is not None


@pytest.mark.asyncio
async def test_admin_flagged_payments_list_and_resolve(client, test_db, monkeypatch):
    """
    Admin endpoints for listing and resolving flagged payments.
    """
    from backend.utils.security import create_access_token
    admin_token = create_access_token({"sub": "admin", "email": "admin@example.com", "role": "admin"})
    headers = {"Authorization": f"Bearer {admin_token}"}

    ref = "ACP-FLAGGED-001"
    await test_db.flagged_payments.insert_one({
        "reference": ref,
        "reason": "amount_mismatch",
        "expected_amount": 5000.0,
        "amount_paid": 5177.67,
        "payload": {
            "id": 888999,
            "status": "success",
            "amount": 517767,
            "customer": {"email": "stuck.student@example.com", "first_name": "Stuck", "last_name": "Student"},
        },
        "flagged_at": datetime.now(timezone.utc),
        "resolved": False,
    })

    # 1. List flagged payments
    res_list = await client.get("/api/admin/flagged-payments", headers=headers)
    assert res_list.status_code == 200
    flagged_list = res_list.json()["flagged_payments"]
    assert any(item["reference"] == ref for item in flagged_list)

    # 2. Resolve flagged payment with force=True
    monkeypatch.setattr("backend.services.payment_completion.process_email_queue", AsyncMock())
    res_resolve = await client.post(
        "/api/admin/flagged-payments/resolve",
        json={"reference": ref, "force": True, "notes": "Customer confirmed on WhatsApp"},
        headers=headers,
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["success"] is True

    # Verify user was created
    user = await test_db.users.find_one({"email": "stuck.student@example.com"})
    assert user is not None
    assert user["library_access_token"] is not None

    # Verify flagged status is now resolved
    flagged_after = await test_db.flagged_payments.find_one({"reference": ref})
    assert flagged_after["resolved"] is True
    assert flagged_after["resolved_by"] == "admin@example.com"


@pytest.mark.asyncio
async def test_admin_paystack_gateway_status_and_sync(client, test_db, monkeypatch):
    """Verify Paystack status endpoint, live transactions, and 1-click sync."""
    admin_token = create_access_token({"sub": "admin", "email": "admin@example.com", "role": "admin"})
    headers = {"Authorization": f"Bearer {admin_token}"}
    monkeypatch.setattr(settings, "PAYSTACK_SECRET_KEY", "sk_test_1234567890abcdef")

    # Mock Paystack API calls
    monkeypatch.setattr(
        "backend.services.paystack.get_paystack_balance",
        AsyncMock(return_value={"status": "success", "data": {"currency": "NGN", "available_balance": 45000.0}}),
    )
    mock_txs = [
        {
            "id": 111,
            "reference": "ACP-PAYSTACK-SYNC-1",
            "amount": 203046,
            "fees": 3046,
            "status": "success",
            "currency": "NGN",
            "channel": "card",
            "paid_at": "2026-10-15T12:00:00Z",
            "customer": {"email": "paystack.sync1@example.com", "first_name": "Sync", "last_name": "One"},
        },
        {
            "id": 222,
            "reference": "ACP-PAYSTACK-SYNC-2",
            "amount": 500000,
            "fees": 7500,
            "status": "success",
            "currency": "NGN",
            "channel": "bank_transfer",
            "paid_at": "2026-10-15T12:10:00Z",
            "customer": {"email": "paystack.sync2@example.com", "first_name": "Sync", "last_name": "Two"},
        },
    ]
    monkeypatch.setattr(
        "backend.services.paystack.list_transactions",
        AsyncMock(return_value={"status": True, "data": mock_txs, "meta": {"total": 2}}),
    )
    monkeypatch.setattr("backend.services.payment_completion.process_email_queue", AsyncMock())

    # 1. Test Status
    res_status = await client.get("/api/admin/paystack/status", headers=headers)
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["connected"] is True
    assert status_data["balance"]["available_balance"] == 45000.0
    assert "webhook" in status_data

    # 2. Test Transactions listing before sync
    res_txs = await client.get("/api/admin/paystack/transactions", headers=headers)
    assert res_txs.status_code == 200
    tx_list = res_txs.json()["transactions"]
    assert len(tx_list) == 2
    assert all(t["sync_status"] == "unreconciled" for t in tx_list)

    # 3. Test 1-click Paystack Sync
    res_sync = await client.post("/api/admin/paystack/sync", headers=headers)
    assert res_sync.status_code == 200
    sync_data = res_sync.json()
    assert sync_data["success"] is True
    assert sync_data["newly_reconciled_count"] == 2

    # 4. Verify users were created in DB
    u1 = await test_db.users.find_one({"email": "paystack.sync1@example.com"})
    u2 = await test_db.users.find_one({"email": "paystack.sync2@example.com"})
    assert u1 is not None and u1["library_access_token"] is not None
    assert u2 is not None and u2["library_access_token"] is not None

    # 5. Subsequent sync shows 0 newly reconciled, 2 already synced
    res_sync_again = await client.post("/api/admin/paystack/sync", headers=headers)
    assert res_sync_again.status_code == 200
    assert res_sync_again.json()["newly_reconciled_count"] == 0
    assert res_sync_again.json()["already_synced"] == 2

