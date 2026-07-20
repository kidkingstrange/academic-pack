"""
Regression coverage for audit Medium #23: sales.py/subscription_scheduler.py
built transactional emails with raw f-string HTML interpolating free-text
fields (customer_name, offer_name), bypassing the Jinja2 autoescape
convention used everywhere else — a name containing HTML/script would
render verbatim in an email sent from the company's real domain.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
from bson import ObjectId

from backend.workers import subscription_scheduler as sub_scheduler_module

MALICIOUS_NAME = '<img src=x onerror=alert(1)> Chidi'


@pytest.mark.asyncio
async def test_subscription_renewal_success_email_escapes_customer_name(test_db, monkeypatch):
    captured = {}

    async def fake_send_email(to, subject, body):
        captured["body"] = body
        return (True, None)

    monkeypatch.setattr(sub_scheduler_module, "send_email", fake_send_email)

    offer_id = ObjectId()
    await test_db.offers.insert_one({"_id": offer_id, "name": "Study Plan", "price": 2000})
    await test_db.subscriptions.insert_one({
        "status": "active", "offer_id": offer_id,
        "next_charge_date": datetime.now(timezone.utc),
        "card_token": "real-token-not-mock",
        "customer_email": "victim@example.com", "customer_name": MALICIOUS_NAME,
        "customer_phone": "+234000", "sales_rep_id": ObjectId(),
    })

    async def fake_charge_authorization(**kwargs):
        return {"status": True, "data": {"status": "success", "amount": 200000}}

    monkeypatch.setattr(sub_scheduler_module, "charge_authorization", fake_charge_authorization)

    await sub_scheduler_module.run_daily_subscription_billing()

    assert "<img src=x onerror=alert(1)>" not in captured["body"]
    assert "&lt;img src=x onerror=alert(1)&gt;" in captured["body"]


@pytest.mark.asyncio
async def test_subscription_cancel_confirm_email_escapes_customer_name(client, test_db, monkeypatch):
    captured = {}

    async def fake_send_email(to, subject, body):
        captured["body"] = body
        return (True, None)

    monkeypatch.setattr("backend.routes.sales.send_email", fake_send_email)

    offer_id = ObjectId()
    await test_db.offers.insert_one({"_id": offer_id, "name": "Study Plan", "price": 2000})
    await test_db.subscriptions.insert_one({
        "status": "active", "offer_id": offer_id,
        "customer_email": "victim2@example.com", "customer_name": MALICIOUS_NAME,
        "cancellation_token": "tok123",
        "cancellation_token_expiry": datetime.now(timezone.utc) + timedelta(hours=1),
    })

    res = await client.post("/api/sales/subscriptions/cancel-confirm", json={"token": "tok123"})
    assert res.status_code == 200
    assert "<img src=x onerror=alert(1)>" not in captured["body"]
    assert "&lt;img src=x onerror=alert(1)&gt;" in captured["body"]
