"""
Unit and integration tests for the dedicated US landing page (/us) and USD payment flows.
"""
import pytest
from unittest.mock import AsyncMock

from backend.routes import payments as payments_module


@pytest.mark.asyncio
async def test_us_landing_route_serves_html(client):
    res = await client.get("/us")
    assert res.status_code == 200
    assert "Stop Studying Harder" in res.text
    assert "MCAT" in res.text
    assert "USMLE" in res.text


@pytest.mark.asyncio
async def test_us_aliases_redirect_to_us(client):
    res_usa = await client.get("/usa", follow_redirects=False)
    assert res_usa.status_code == 301
    assert res_usa.headers["location"] == "/us"

    res_united = await client.get("/united-states", follow_redirects=False)
    assert res_united.status_code == 301
    assert res_united.headers["location"] == "/us"


@pytest.mark.asyncio
async def test_nigerian_landing_remains_intact(client):
    res = await client.get("/")
    assert res.status_code == 200
    assert "SCALE GROUP" in res.text
    assert "Complete 7-Book Study System" in res.text


@pytest.mark.asyncio
async def test_usd_payment_initialization_pricing_and_currency(client, test_db, monkeypatch):
    captured_paystack_call = {}

    async def fake_initialize_transaction(email, amount_naira, reference, callback_url, metadata=None, channels=None, currency=None, subaccount=None):
        captured_paystack_call["amount"] = amount_naira
        captured_paystack_call["currency"] = currency
        return {
            "authorization_url": "https://checkout.paystack.com/us-access-code",
            "access_code": "us_access_code_123",
            "reference": reference,
        }

    monkeypatch.setattr(payments_module, "initialize_transaction", fake_initialize_transaction)

    res = await client.post("/api/payments/initialize", json={
        "name": "Sarah Miller",
        "email": "sarah.miller@example.com",
        "country": "US",
        "currency": "USD",
        "payment_method": "card",
    })

    assert res.status_code == 200
    data = res.json()
    assert data["amount"] == 15.0  # Launch price $15
    assert data["action"] == "redirect"
    assert captured_paystack_call["amount"] == 15.0
    assert captured_paystack_call["currency"] == "USD"

    pending = await test_db.pending_payments.find_one({"reference": data["reference"]})
    assert pending is not None
    assert pending["amount"] == 15.0
    assert pending["currency"] == "USD"
