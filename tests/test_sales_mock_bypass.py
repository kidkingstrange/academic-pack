"""
Regression coverage for the sales.py mock-payment backdoor in development/production environments.
"""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from bson import ObjectId

from backend.config import get_settings
from backend.routes import sales as sales_module
from backend.workers import subscription_scheduler as sub_scheduler_module


async def _make_lead_and_offer(db):
    offer_id = ObjectId()
    await db.offers.insert_one({
        "_id": offer_id, "name": "Test Offer", "description": "d",
        "price": 2000, "billing_type": "one_time",
    })
    token = "test-checkout-token"
    await db.sales_leads.insert_one({
        "generated_link_token": token, "status": "link_generated",
        "offer_id": offer_id, "prospect_email": "prospect@example.com",
        "prospect_name": "Prospect", "prospect_phone": "+2340000000",
        "sales_rep_id": ObjectId(), "created_at": datetime.now(timezone.utc),
    })
    return token, offer_id


@pytest.mark.asyncio
async def test_mock_payment_bypass_works_in_development(client, test_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    monkeypatch.setattr(sales_module, "settings", get_settings())
    token, _ = await _make_lead_and_offer(test_db)

    res = await client.post("/api/sales/checkout/pay", json={
        "token": token, "payment_method_id": "mock-payment-method-id",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"

    pending = await test_db.pending_subscription_payments.find_one({"reference": data["reference"]})
    assert pending["charge_id"].startswith("MOCK-")


@pytest.mark.asyncio
async def test_mock_payment_bypass_blocked_in_production(client, test_db, monkeypatch):
    """With APP_ENV=production, the mock payment_method_id must NOT take the
    instant-fake-success shortcut — it must fall through to the real
    Paystack charge path instead."""
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    monkeypatch.setattr(sales_module, "settings", get_settings())
    token, _ = await _make_lead_and_offer(test_db)

    async def fake_initialize_transaction(**kwargs):
        raise RuntimeError("real charge path was correctly reached")

    monkeypatch.setattr(sales_module, "initialize_transaction", fake_initialize_transaction)

    res = await client.post("/api/sales/checkout/pay", json={
        "token": token, "payment_method_id": "mock-payment-method-id",
    })
    assert res.status_code == 502
    assert "real charge path was correctly reached" in res.json()["detail"]

    pending = await test_db.pending_subscription_payments.find_one({})
    assert pending is None


@pytest.mark.asyncio
async def test_mock_charge_verify_blocked_in_production(client, test_db, monkeypatch):
    """Defense in depth: even if a MOCK- pending record somehow exists in
    production, /checkout/verify must not simulate a successful charge for
    it — it must attempt a real gateway verification instead."""
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    monkeypatch.setattr(sales_module, "settings", get_settings())
    ref = "SUB-LEFTOVER-MOCK"
    await test_db.pending_subscription_payments.insert_one({
        "reference": ref, "charge_id": "MOCK-LEFTOVER123",
        "lead_token": "x", "status": "pending",
        "created_at": datetime.now(timezone.utc),
    })

    async def fake_verify_transaction(reference):
        raise RuntimeError("real verification path was correctly reached")

    monkeypatch.setattr(sales_module, "verify_transaction", fake_verify_transaction)

    res = await client.post("/api/sales/checkout/verify", json={"reference": ref})
    assert res.status_code == 502


@pytest.mark.asyncio
async def test_subscription_renewal_mock_bypass_blocked_in_production(test_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    monkeypatch.setattr(sub_scheduler_module, "settings", get_settings())

    offer_id = ObjectId()
    await test_db.offers.insert_one({"_id": offer_id, "name": "Sub Offer", "price": 2000})
    sub_id = (await test_db.subscriptions.insert_one({
        "status": "active", "offer_id": offer_id,
        "next_charge_date": datetime.now(timezone.utc),
        "card_token": "mock-card-token-12345",
        "customer_email": "subcustomer@example.com",
        "customer_name": "Sub Customer", "customer_phone": "+234000",
        "sales_rep_id": ObjectId(),
    })).inserted_id

    async def fake_charge_authorization(**kwargs):
        raise RuntimeError("real charge_authorization path was correctly reached")

    monkeypatch.setattr(sub_scheduler_module, "charge_authorization", fake_charge_authorization)
    monkeypatch.setattr(sub_scheduler_module, "send_email", AsyncMock(return_value=(True, None)))

    await sub_scheduler_module.run_daily_subscription_billing()

    sub = await test_db.subscriptions.find_one({"_id": sub_id})
    assert sub["status"] == "past_due"
