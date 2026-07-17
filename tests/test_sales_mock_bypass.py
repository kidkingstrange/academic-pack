"""
Regression coverage for the sales.py mock-payment backdoor (audit Critical
#3/#4/#5): "mock-payment-method-id" / "mock-card-token-12345" used to
fabricate a successful charge with no environment gate, and the real
(non-mock) charge path crashed with NameError on an undefined FLW_API_BASE.
"""
import httpx
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from bson import ObjectId

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
    monkeypatch.setattr(sales_module.settings, "APP_ENV", "development")
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
    Flutterwave charge path instead."""
    monkeypatch.setattr(sales_module.settings, "APP_ENV", "production")
    token, _ = await _make_lead_and_offer(test_db)

    class RealPathAttempted(Exception):
        pass

    async def fake_get_flw_token():
        raise RealPathAttempted("real charge path was correctly reached")

    monkeypatch.setattr(sales_module, "get_flw_token", fake_get_flw_token)

    with pytest.raises(RealPathAttempted):
        await client.post("/api/sales/checkout/pay", json={
            "token": token, "payment_method_id": "mock-payment-method-id",
        })

    # No fabricated pending_subscription_payments record should exist.
    pending = await test_db.pending_subscription_payments.find_one({})
    assert pending is None


@pytest.mark.asyncio
async def test_mock_charge_verify_blocked_in_production(client, test_db, monkeypatch):
    """Defense in depth: even if a MOCK- pending record somehow exists in
    production, /checkout/verify must not simulate a successful charge for
    it — it must attempt a real gateway verification instead."""
    monkeypatch.setattr(sales_module.settings, "APP_ENV", "production")
    ref = "SUB-LEFTOVER-MOCK"
    await test_db.pending_subscription_payments.insert_one({
        "reference": ref, "charge_id": "MOCK-LEFTOVER123",
        "lead_token": "x", "status": "pending",
        "created_at": datetime.now(timezone.utc),
    })

    async def fake_verify_flw_charge(charge_id):
        raise RuntimeError("real verification path was correctly reached")

    monkeypatch.setattr(sales_module, "verify_flw_charge", fake_verify_flw_charge)

    res = await client.post("/api/sales/checkout/verify", json={"reference": ref})
    assert res.status_code == 502  # real gateway call failed, not a fabricated success


@pytest.mark.asyncio
async def test_flw_api_base_is_defined_for_real_charge_path(client, test_db, monkeypatch):
    """The real (non-mock) charge path used to crash with NameError because
    FLW_API_BASE was never imported. Confirm it resolves and gets used."""
    monkeypatch.setattr(sales_module.settings, "APP_ENV", "production")
    token, _ = await _make_lead_and_offer(test_db)

    monkeypatch.setattr(sales_module, "get_flw_token", AsyncMock(return_value="fake-token"))

    captured_urls = []

    class FakeResponse:
        def json(self):
            return {"status": "success", "data": {"id": "chg_1", "next_action": {}}}

    class FakeAsyncClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def post(self, url, **kwargs):
            captured_urls.append(url)
            return FakeResponse()

    # sales.py does `import httpx` locally inside the route function, not at
    # module level, so it re-reads httpx.AsyncClient from sys.modules at call
    # time — patching the real httpx module's attribute here is what it sees.
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: FakeAsyncClient())

    res = await client.post("/api/sales/checkout/pay", json={
        "token": token, "payment_method_id": "real-card-pm-123",
    })
    assert res.status_code == 200
    assert captured_urls, "the real charge path never actually ran"
    assert any(u.startswith(sales_module.FLW_API_BASE) for u in captured_urls)
    assert any("/charges" in u for u in captured_urls)


@pytest.mark.asyncio
async def test_subscription_renewal_mock_bypass_blocked_in_production(test_db, monkeypatch):
    monkeypatch.setattr(sub_scheduler_module.settings, "APP_ENV", "production")

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

    async def fake_charge_token(**kwargs):
        raise RuntimeError("real charge_token path was correctly reached")

    monkeypatch.setattr(sub_scheduler_module, "charge_token", fake_charge_token)
    monkeypatch.setattr(sub_scheduler_module, "get_flw_token", AsyncMock(return_value="fake-token"))
    monkeypatch.setattr(sub_scheduler_module, "send_email", AsyncMock(return_value=(True, None)))

    await sub_scheduler_module.run_daily_subscription_billing()

    sub = await test_db.subscriptions.find_one({"_id": sub_id})
    # A real (failing) charge attempt was made — the subscription must be
    # marked past_due, not silently "renewed" via the mock shortcut.
    assert sub["status"] == "past_due"
