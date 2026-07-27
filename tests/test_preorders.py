"""
Automated unit and integration tests for Pre-Orders flow and Admin Fulfillment.
"""
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_preorder_initialization(client, monkeypatch):
    mock_init = AsyncMock(return_value={
        "authorization_url": "https://checkout.paystack.com/test-preorder-url",
        "access_code": "ACCESS_PRE_123",
        "reference": "ACP-PRE-TEST1",
    })
    monkeypatch.setattr("backend.routes.preorders.initialize_transaction", mock_init)

    res = await client.post("/api/payments/preorder/initialize", json={
        "name": "Jane Preorder",
        "email": "jane@example.com",
        "book_id": "how-to-close-high-paying-clients-in-the-dms",
        "book_title": "How to Close High-Paying Clients in the DMs",
        "amount": 5000,
        "payment_method": "pay_with_bank",
    })

    assert res.status_code == 200
    data = res.json()
    assert data["action"] == "redirect"
    assert "https://checkout.paystack.com" in data["redirect_url"]


@pytest.mark.asyncio
async def test_preorder_verification_creates_db_record(client, test_db, monkeypatch):
    mock_verify = AsyncMock(return_value={
        "status": True,
        "data": {
            "status": "success",
            "id": 987654,
            "amount": 500000,
        }
    })
    monkeypatch.setattr("backend.routes.preorders.verify_transaction", mock_verify)

    ref = "ACP-PRE-VERIFY1"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "email": "janedoe@example.com",
        "name": "Jane Doe",
        "book_id": "naira-ads",
        "book_title": "Naira Ads Masterclass",
        "amount": 5000,
        "is_preorder": True,
    })

    res = await client.post("/api/payments/preorder/verify", json={
        "reference": ref,
        "email": "janedoe@example.com",
        "name": "Jane Doe",
        "book_id": "naira-ads",
        "book_title": "Naira Ads Masterclass",
    })

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "7 days" in data["message"]

    # Verify db.pre_orders record exists and delivered is False
    po = await test_db.pre_orders.find_one({"reference": ref})
    assert po is not None
    assert po["email"] == "janedoe@example.com"
    assert po["delivered"] is False
    assert po["amount"] == 5000.0


@pytest.mark.asyncio
async def test_customer_refund_request(client, test_db):
    ref = "ACP-PRE-REFUND1"
    await test_db.pre_orders.insert_one({
        "reference": ref,
        "email": "buyer@example.com",
        "name": "Buyer Person",
        "book_id": "book1",
        "book_title": "Academic Comeback Package",
        "amount": 5000,
        "delivered": False,
        "refund_requested": False,
    })

    res = await client.post("/api/preorders/request-refund", json={
        "reference": ref,
        "email": "buyer@example.com",
        "reason": "Delivery taking too long",
    })

    assert res.status_code == 200
    assert res.json()["success"] is True

    po = await test_db.pre_orders.find_one({"reference": ref})
    assert po["refund_requested"] is True
    assert po["refund_reason"] == "Delivery taking too long"


from backend.utils.security import create_access_token

@pytest.mark.asyncio
async def test_admin_preorders_fulfillment_workflow(client, test_db):
    token = create_access_token({"sub": "admin", "email": "admin@example.com", "role": "admin"})
    admin_headers = {"Authorization": f"Bearer {token}"}

    # Insert 2 preorders
    await test_db.pre_orders.insert_one({
        "reference": "ACP-PRE-ADM1",
        "email": "customer1@example.com",
        "name": "Customer One",
        "book_id": "b1",
        "book_title": "Book 1",
        "amount": 5000,
        "delivered": False,
    })

    # Fetch admin preorders
    res = await client.get("/api/admin/preorders", headers=admin_headers)
    assert res.status_code == 200
    preorders = res.json()["pre_orders"]
    assert len(preorders) >= 1

    po_id = preorders[0]["id"]

    # Mark as delivered
    del_res = await client.post(f"/api/admin/preorders/{po_id}/deliver", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    updated_po = await test_db.pre_orders.find_one({"reference": "ACP-PRE-ADM1"})
    assert updated_po["delivered"] is True
