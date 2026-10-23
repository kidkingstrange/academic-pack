"""
Comprehensive end-to-end test suite for the new book product:
"Quitting The Handjob: How to Stop Masturbation and Pornography Addiction Forever" by David Itoya.
"""
import hashlib
import hmac
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId

from backend.config import get_settings
from backend.services.payment_completion import complete_payment
from backend.utils.product_delivery import resolve_product_pdf_path

settings = get_settings()
WEBHOOK_URL = "/api/payments/webhook"


def _sign(raw_body: bytes) -> str:
    secret = (settings.PAYSTACK_SECRET_KEY or "").strip()
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()


def _payload(ref: str, email: str = "customer@example.com", amount_naira: float = 5000):
    return {
        "event": "charge.success",
        "data": {
            "status": "success",
            "reference": ref,
            "id": 998877,
            "amount": int(amount_naira * 100),
            "customer": {"email": email, "first_name": "David", "last_name": "Test"},
        },
    }


@pytest.mark.asyncio
async def test_product_database_registration_and_pdf_resolution(test_db):
    """Product is registered in the products collection and its PDF resolves cleanly."""
    from scripts.sync_products_db import CANONICAL_PRODUCTS
    
    # Ensure products are synced in test db
    for prod in CANONICAL_PRODUCTS:
        selector = {"order": prod["order"]} if "order" in prod else {"slug": prod.get("slug", prod["title"])}
        await test_db.products.update_one(
            selector,
            {"$set": prod},
            upsert=True,
        )

    product = await test_db.products.find_one({"slug": "quitting-the-handjob"})
    assert product is not None
    assert product["price_naira"] == 5000
    assert "Quitting The Handjob" in product["title"]
    assert product["file_path"] == "Quitting_The_Handjob_David_Itoya.pdf"

    resolved_path = resolve_product_pdf_path(product, settings.UPLOADS_DIR)
    assert resolved_path is not None
    assert resolved_path.exists()
    assert resolved_path.name == "Quitting_The_Handjob_David_Itoya.pdf"


@pytest.mark.asyncio
async def test_sales_page_routes_and_og_tags(client):
    """The new sales page is served across all URL aliases with proper metadata."""
    routes_to_test = [
        "/quitting-the-handjob",
        "/quitting-the-handjob.html",
        "/books/quitting-the-handjob",
    ]
    for route in routes_to_test:
        res = await client.get(route)
        assert res.status_code == 200, f"Route {route} failed with status {res.status_code}"
        html = res.text
        assert "Quitting The Handjob" in html
        assert "David Itoya" in html
        assert "₦5,000" in html
        assert 'property="og:image"' in html
        assert "quitting-the-handjob.webp" in html
        assert "window.PRODUCT_SLUG = 'quitting-the-handjob'" in html

    # Verify cover image is served with 200 OK
    img_res = await client.get("/book-covers/quitting-the-handjob.webp")
    assert img_res.status_code == 200
    assert len(img_res.content) > 1000


@pytest.mark.asyncio
async def test_payment_initialization_authoritative_price_and_reference(client, test_db, monkeypatch):
    """Payment initialization generates an ACP-QTH- reference and enforces ₦5,000 base price."""
    monkeypatch.setattr(
        "backend.routes.payments.initialize_transaction",
        AsyncMock(return_value={
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/mock-qth",
                "reference": "ACP-QTH-12345",
            }
        })
    )

    req_body = {
        "name": "Chidi Test",
        "email": "chidi.test@example.com",
        "product_slug": "quitting-the-handjob",
        "payment_method": "card",
    }
    res = await client.post("/api/payments/initialize", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert data["reference"].startswith("ACP-QTH-")
    assert data["amount"] == 5000

    pending = await test_db.pending_payments.find_one({"reference": data["reference"]})
    assert pending is not None
    assert pending["amount"] == 5000
    assert pending["product_slug"] == "quitting-the-handjob"


@pytest.mark.asyncio
async def test_payment_initialization_viral_friend_discount(client, test_db, monkeypatch):
    """3 valid friend emails trigger the ₦4,000 discount tier for the product."""
    monkeypatch.setattr(
        "backend.routes.payments.initialize_transaction",
        AsyncMock(return_value={
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/mock-qth",
                "reference": "ACP-QTH-DISCOUNT-1",
            }
        })
    )

    req_body = {
        "name": "Friend Referrer",
        "email": "referrer@example.com",
        "product_slug": "quitting-the-handjob",
        "payment_method": "card",
        "friend_emails": [
            "friend1@example.com",
            "friend2@example.com",
            "friend3@example.com",
        ]
    }
    res = await client.post("/api/payments/initialize", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert data["amount"] == 4000


@pytest.mark.asyncio
async def test_webhook_payment_completion_entitlement_and_affiliate_attribution(
    client, test_db, monkeypatch
):
    """Webhook verifies signature, completes payment, records entitlement and 60% affiliate commission."""
    monkeypatch.setattr("backend.routes.payments.send_email", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr("backend.services.payment_completion.process_email_queue", AsyncMock())

    await test_db.payments.create_index("reference", unique=True)
    await test_db.referrals.create_index("reference", unique=True)

    # 1. Setup canonical product in test_db
    prod_id = ObjectId()
    await test_db.products.insert_one({
        "_id": prod_id,
        "title": "Quitting The Handjob",
        "slug": "quitting-the-handjob",
        "price": 5000,
        "file_name": "Quitting_The_Handjob_David_Itoya.pdf",
        "is_active": True,
        "order": 8,
    })

    # 2. Setup affiliate
    await test_db.affiliates.insert_one({
        "code": "QTHVIP",
        "name": "Top Affiliate",
        "email": "affiliate@example.com",
        "active": True,
        "commission_percent": 60.0,
    })

    ref = "ACP-QTH-TEST-VERIFY-1"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "email": "buyer@example.com",
        "name": "Eager Buyer",
        "amount": 5000,
        "commission_base_price": 5000,
        "product_slug": "quitting-the-handjob",
        "referred_by": "QTHVIP",
    })

    # 3. Simulate Paystack webhook
    body = _payload(ref, email="buyer@example.com", amount_naira=5000)
    raw = json.dumps(body).encode("utf-8")
    sig = _sign(raw)

    res = await client.post(
        WEBHOOK_URL,
        content=raw,
        headers={"Content-Type": "application/json", "x-paystack-signature": sig},
    )
    assert res.status_code == 200

    # 4. Verify payment record
    payment = await test_db.payments.find_one({"reference": ref})
    assert payment is not None
    assert payment["product_slug"] == "quitting-the-handjob"
    assert payment["amount"] == 5000

    # 5. Verify user entitlement
    user = await test_db.users.find_one({"email": "buyer@example.com"})
    assert user is not None
    assert str(prod_id) in user["purchased_products"]
    assert "quitting-the-handjob" in user["purchased_products"]

    # 6. Verify affiliate referral received 60% of ₦5,000 = ₦3,000
    ref_rec = await test_db.referrals.find_one({"reference": ref})
    assert ref_rec is not None
    assert ref_rec["affiliate_code"] == "QTHVIP"
    assert ref_rec["commission_amount"] == 3000.0


@pytest.mark.asyncio
async def test_webhook_idempotency_avoids_duplicate_orders_and_commissions(
    client, test_db, monkeypatch
):
    """Replaying the exact same webhook must be strictly idempotent."""
    monkeypatch.setattr("backend.routes.payments.send_email", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr("backend.services.payment_completion.process_email_queue", AsyncMock())

    await test_db.payments.create_index("reference", unique=True)
    await test_db.referrals.create_index("reference", unique=True)

    prod_id = ObjectId()
    await test_db.products.insert_one({
        "_id": prod_id,
        "title": "Quitting The Handjob",
        "slug": "quitting-the-handjob",
        "price": 5000,
        "file_name": "Quitting_The_Handjob_David_Itoya.pdf",
        "is_active": True,
        "order": 8,
    })

    await test_db.affiliates.insert_one({
        "code": "IDEMPOTENT_AFF",
        "active": True,
        "commission_percent": 60.0,
    })

    ref = "ACP-QTH-IDEMPOTENT-001"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "email": "idem@example.com",
        "name": "Idem Customer",
        "amount": 5000,
        "commission_base_price": 5000,
        "product_slug": "quitting-the-handjob",
        "referred_by": "IDEMPOTENT_AFF",
    })

    body = _payload(ref, email="idem@example.com", amount_naira=5000)
    raw = json.dumps(body).encode("utf-8")
    sig = _sign(raw)

    # First call
    res1 = await client.post(
        WEBHOOK_URL,
        content=raw,
        headers={"Content-Type": "application/json", "x-paystack-signature": sig},
    )
    assert res1.status_code == 200

    # Second call (replay)
    res2 = await client.post(
        WEBHOOK_URL,
        content=raw,
        headers={"Content-Type": "application/json", "x-paystack-signature": sig},
    )
    assert res2.status_code == 200

    # Verify single payment record
    payments_count = await test_db.payments.count_documents({"reference": ref})
    assert payments_count == 1

    # Verify single referral record
    referrals_count = await test_db.referrals.count_documents({"reference": ref})
    assert referrals_count == 1


@pytest.mark.asyncio
async def test_library_product_unlock_and_signed_download(client, test_db):
    """User with entitlement can sign and download the book file; unauthorized user is blocked."""
    prod_id = ObjectId()
    await test_db.products.insert_one({
        "_id": prod_id,
        "title": "Quitting The Handjob",
        "slug": "quitting-the-handjob",
        "price": 5000,
        "file_name": "Quitting_The_Handjob_David_Itoya.pdf",
        "description": "How to stop masturbation and pornography addiction forever.",
        "is_active": True,
        "order": 8,
    })

    # Authorized user
    auth_token = "valid-qth-token-123"
    await test_db.users.insert_one({
        "name": "Authorized Reader",
        "email": "reader@example.com",
        "library_access_token": auth_token,
        "purchased_products": [str(prod_id), "quitting-the-handjob"],
    })

    # Unauthorized user
    unauth_token = "unauth-token-456"
    await test_db.users.insert_one({
        "name": "Locked Reader",
        "email": "locked@example.com",
        "library_access_token": unauth_token,
        "purchased_products": [],
    })

    # 1. Check get_library lock status
    lib_res = await client.get(f"/api/library?token={auth_token}")
    assert lib_res.status_code == 200
    lib_data = lib_res.json()
    qth_item = next(p for p in lib_data["products"] if p["id"] == str(prod_id))
    assert qth_item["locked"] is False

    locked_lib_res = await client.get(f"/api/library?token={unauth_token}")
    assert locked_lib_res.status_code == 200
    locked_item = next(p for p in locked_lib_res.json()["products"] if p["id"] == str(prod_id))
    assert locked_item["locked"] is True

    # 2. Unauthorized attempt to sign download
    blocked_sign = await client.get(f"/api/library/sign/{prod_id}?token={unauth_token}")
    assert blocked_sign.status_code == 403

    # 3. Authorized signing and download
    sign_res = await client.get(f"/api/library/sign/{prod_id}?token={auth_token}")
    assert sign_res.status_code == 200
    sign_data = sign_res.json()
    assert "signed_url" in sign_data

    # 4. Fetch the file using signed URL
    file_res = await client.get(sign_data["signed_url"])
    assert file_res.status_code == 200
    assert file_res.headers["content-type"] == "application/pdf"
    assert len(file_res.content) > 1000
