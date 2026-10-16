"""
Tests for Paystack Auto-Sync Background Reconciliation and Executive Command Center Accuracy.

Verifies:
1. Successful Paystack transactions are automatically synced and reconciled into db.payments.
2. Verified_at timestamps match Paystack paid_at, ensuring accurate daily/weekly/monthly revenue reporting.
3. String/Null verified_at and amount formats are automatically sanitized and aggregated properly.
4. Dynamic webhook URL generation for edgepack.thescaleconference.com.
5. Executive Command Center (/api/admin/analytics/overview) reflects up-to-date KPIs after sync.
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from backend.config import get_settings
from backend.utils.security import create_access_token
from backend.services.paystack_sync_service import (
    auto_sync_paystack_successful_sales,
    sanitize_payment_records,
)

settings = get_settings()


@pytest.fixture
def admin_headers():
    token = create_access_token({"sub": "admin", "email": "admin@example.com", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_auto_sync_paystack_successful_sales(test_db, monkeypatch):
    """
    Test that auto_sync_paystack_successful_sales pulls successful transactions
    from Paystack and accurately reconciles them into db.payments with the original timestamp.
    """
    monkeypatch.setattr(settings, "PAYSTACK_SECRET_KEY", "sk_live_test_secret_key_12345")
    monkeypatch.setattr("backend.services.payment_completion.process_email_queue", AsyncMock())

    now = datetime.now(timezone.utc)
    yesterday_iso = (now - timedelta(days=1)).strftime("%Y-%m-%dT14:30:00.000Z")

    mock_paystack_response = {
        "status": True,
        "message": "Transactions retrieved",
        "data": [
            {
                "id": 10001,
                "reference": "ACP-AUTO-SYNC-001",
                "status": "success",
                "amount": 517767,  # ₦5,177.67
                "fees": 17767,
                "currency": "NGN",
                "channel": "bank_transfer",
                "paid_at": yesterday_iso,
                "customer": {
                    "email": "student.synced1@example.com",
                    "first_name": "Tunde",
                    "last_name": "Bakare",
                },
            },
            {
                "id": 10002,
                "reference": "ACP-AUTO-SYNC-002",
                "status": "success",
                "amount": 500000,  # ₦5,000.00
                "fees": 7500,
                "currency": "NGN",
                "channel": "card",
                "paid_at": yesterday_iso,
                "customer": {
                    "email": "student.synced2@example.com",
                    "first_name": "Chidinma",
                    "last_name": "Eze",
                },
            },
        ],
    }

    # Also insert pending payment for 001 with base_price 5000
    await test_db.pending_payments.insert_one({
        "reference": "ACP-AUTO-SYNC-001",
        "email": "student.synced1@example.com",
        "name": "Tunde Bakare",
        "amount": 5000.0,
        "base_price": 5000.0,
        "tier": "complete",
        "created_at": now - timedelta(days=1),
    })

    with patch("backend.services.paystack.list_transactions", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = mock_paystack_response

        res = await auto_sync_paystack_successful_sales(test_db, per_page=50, force=True)
        assert res["success"] is True
        assert res["newly_reconciled_count"] == 2
        assert len(res["newly_reconciled"]) == 2

    # Verify records were inserted in db.payments
    p1 = await test_db.payments.find_one({"reference": "ACP-AUTO-SYNC-001"})
    assert p1 is not None
    assert p1["status"] == "success"
    assert p1["amount"] == 5000.0
    assert p1["completed_via"] == "paystack_auto_sync"
    assert isinstance(p1["verified_at"], datetime)

    # Verify paid_at was parsed correctly as yesterday
    assert p1["verified_at"].day == (now - timedelta(days=1)).day

    p2 = await test_db.payments.find_one({"reference": "ACP-AUTO-SYNC-002"})
    assert p2 is not None
    assert p2["status"] == "success"
    assert p2["amount"] == 5000.0

    # Running sync again without force or with force=True should recognize both as already synced
    with patch("backend.services.paystack.list_transactions", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = mock_paystack_response
        res2 = await auto_sync_paystack_successful_sales(test_db, per_page=50, force=True)
        assert res2["already_synced"] == 2
        assert res2["newly_reconciled_count"] == 0


@pytest.mark.asyncio
async def test_sanitize_payment_records(test_db):
    """
    Test that sanitize_payment_records corrects string dates, missing verified_at,
    and string amounts so Mongo aggregations never fail.
    """
    now = datetime.now(timezone.utc)
    # Payment with string verified_at and string amount
    await test_db.payments.insert_one({
        "reference": "ACP-LEGACY-STR",
        "email": "legacy.str@example.com",
        "name": "Legacy String",
        "amount": "4000",
        "status": "success",
        "verified_at": "2026-10-15T12:00:00Z",
        "created_at": "2026-10-15T12:00:00Z",
    })

    # Payment with missing verified_at
    await test_db.payments.insert_one({
        "reference": "ACP-LEGACY-MISSING-DATE",
        "email": "legacy.nodate@example.com",
        "name": "No Date",
        "amount": 2000.0,
        "status": "success",
        "created_at": now - timedelta(days=2),
    })

    fixed = await sanitize_payment_records(test_db)
    assert fixed >= 2

    p_str = await test_db.payments.find_one({"reference": "ACP-LEGACY-STR"})
    assert isinstance(p_str["verified_at"], datetime)
    assert isinstance(p_str["amount"], float)
    assert p_str["amount"] == 4000.0

    p_missing = await test_db.payments.find_one({"reference": "ACP-LEGACY-MISSING-DATE"})
    assert isinstance(p_missing["verified_at"], datetime)
    assert p_missing["verified_at"].day == (now - timedelta(days=2)).day


@pytest.mark.asyncio
async def test_analytics_overview_reflects_synced_revenue(client, test_db, admin_headers, monkeypatch):
    """
    Test that /api/admin/analytics/overview automatically syncs Paystack
    and accurately calculates Total, Today, Weekly, and Monthly revenue.
    """
    monkeypatch.setattr(settings, "PAYSTACK_SECRET_KEY", "sk_live_test_key_xyz")
    monkeypatch.setattr("backend.services.payment_completion.process_email_queue", AsyncMock())

    now = datetime.now(timezone.utc)
    today_iso = now.strftime("%Y-%m-%dT10:00:00.000Z")
    yesterday_iso = (now - timedelta(days=1)).strftime("%Y-%m-%dT15:00:00.000Z")

    mock_paystack_response = {
        "status": True,
        "message": "Transactions retrieved",
        "data": [
            {
                "id": 20001,
                "reference": "ACP-DASH-TODAY",
                "status": "success",
                "amount": 500000,
                "currency": "NGN",
                "channel": "card",
                "paid_at": today_iso,
                "customer": {"email": "dash.today@example.com", "first_name": "Today", "last_name": "Buyer"},
            },
            {
                "id": 20002,
                "reference": "ACP-DASH-YESTERDAY",
                "status": "success",
                "amount": 500000,
                "currency": "NGN",
                "channel": "bank_transfer",
                "paid_at": yesterday_iso,
                "customer": {"email": "dash.yesterday@example.com", "first_name": "Yesterday", "last_name": "Buyer"},
            },
        ],
    }

    with patch("backend.services.paystack.list_transactions", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = mock_paystack_response

        # Request analytics overview with force_sync=true
        res = await client.get("/api/admin/analytics/overview?period=all&force_sync=true", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()

        # Both transactions (₦5,000 each = ₦10,000) must be reflected
        assert data["total_sales"] == 2
        assert data["total_revenue"] == 10000.0
        assert data["today_revenue"] == 5000.0
        assert data["week_revenue"] == 10000.0
        assert data["month_revenue"] == 10000.0
        assert data["aov"] == 5000.0
        assert len(data["recent_transactions"]) == 2
        assert "last_synced_at" in data


@pytest.mark.asyncio
async def test_paystack_gateway_status_dynamic_domain(client, test_db, admin_headers, monkeypatch):
    """
    Test that /api/admin/paystack/status dynamically returns
    https://edgepack.thescaleconference.com/api/payments/webhook
    instead of the hardcoded Render domain.
    """
    monkeypatch.setattr(settings, "PAYSTACK_SECRET_KEY", "sk_live_test_key_abc")
    monkeypatch.setattr(
        "backend.services.paystack.get_paystack_balance",
        AsyncMock(return_value={"status": "success", "data": {"available_balance": 150000.0}}),
    )

    # When request comes with Host: edgepack.thescaleconference.com
    headers = {**admin_headers, "Host": "edgepack.thescaleconference.com"}
    res = await client.get("/api/admin/paystack/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["connected"] is True
    assert data["mode"] == "live"
    assert data["webhook"]["expected_url"] == "https://edgepack.thescaleconference.com/api/payments/webhook"
