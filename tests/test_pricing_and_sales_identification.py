"""
Comprehensive automated tests for:
1. Product pricing and promotional lifecycle (₦5,000 promo until 1 Jan 2027 -> ₦20,000 regular).
2. Backend price validation and anti-tampering enforcement.
3. Single books pricing retention (₦5,000).
4. Sales identification with exact product names, SKUs, quantities, and line items.
5. Historical transaction safety and resolution.
6. Webhook idempotency (no duplicate sales/items).
7. Admin analytics sales API responses.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from backend.routes.payments import compute_price_and_referral
from backend.services.payment_completion import complete_payment
from backend.utils.canonical_products import (
    is_academic_comeback_promo_active,
    get_package_price,
    build_order_items,
    resolve_payment_items,
    get_canonical_price,
    CANONICAL_PRODUCTS,
)
from backend.utils.security import create_access_token
from backend.config import get_settings

settings = get_settings()


# ── PRICING SCENARIOS ─────────────────────────────────────────────────────────

def test_promo_active_before_2027():
    """Verify promo is active today (2026) and ends on 1st of January 2027."""
    assert is_academic_comeback_promo_active() is True
    assert get_package_price("NGN") == 5000.0
    assert get_package_price("USD") == 15.0


def test_promo_transitions_to_20000_after_jan_1_2027():
    """Verify package automatically transitions to ₦20,000 after 1 Jan 2027."""
    after_date = datetime(2027, 1, 1, 0, 0, 1, tzinfo=timezone.utc)
    assert is_academic_comeback_promo_active(after_date) is False
    assert get_package_price("NGN", after_date) == 20000.0
    assert get_package_price("USD", after_date) == 40.0


def test_canonical_books_retain_exact_price():
    """Verify all 12 standalone canonical books retain their authoritative ₦5,000 price."""
    assert len(CANONICAL_PRODUCTS) == 12
    for prod in CANONICAL_PRODUCTS:
        assert prod["price_naira"] == 5000
        assert prod["price_usd"] == 15.0
        assert prod.get("sku") == f"BOOK-{prod['slug'].upper()}"
        assert get_canonical_price(slug=prod["slug"]) == 5000.0


@pytest.mark.asyncio
async def test_bundle_initialization_charges_5000(client, test_db, monkeypatch):
    """Verify checkout initializes the Academic Comeback Package at ₦5,000."""
    monkeypatch.setattr(
        "backend.routes.payments.initialize_transaction",
        AsyncMock(return_value={"authorization_url": "https://checkout.paystack.com/test", "access_code": "code_123"})
    )

    resp = await client.post(
        "/api/payments/initialize",
        json={
            "email": "student_buyer@example.com",
            "name": "Jane Student",
            "currency": "NGN",
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["amount"] == 5000.0
    assert data["reference"].startswith("ACP-")

    # Verify pending payment stored structured item snapshot
    pending = await test_db.pending_payments.find_one({"reference": data["reference"]})
    assert pending is not None
    assert pending["product_name"] == "The Academic Comeback Package"
    assert pending["product_sku"] == "ACP-BUNDLE"
    assert pending["amount"] == 5000.0
    assert len(pending["items"]) == 1
    assert pending["items"][0]["name"] == "The Academic Comeback Package"
    assert pending["items"][0]["product_sku"] == "ACP-BUNDLE"
    assert pending["items"][0]["quantity"] == 1
    assert pending["items"][0]["unit_price"] == 5000.0


@pytest.mark.asyncio
async def test_backend_price_tampering_protection(client, test_db, monkeypatch):
    """Verify backend calculates price independently and ignores client manipulation."""
    captured_init_amount = None

    async def mock_init(email, amount_naira, reference, **kwargs):
        nonlocal captured_init_amount
        captured_init_amount = amount_naira
        return {"authorization_url": "https://checkout.paystack.com/test", "access_code": "code_123"}

    monkeypatch.setattr("backend.routes.payments.initialize_transaction", mock_init)

    # Client attempts to pass amount=1000 in payload (or custom price tampering)
    resp = await client.post(
        "/api/payments/initialize",
        json={
            "email": "hacker@example.com",
            "name": "Sneaky User",
            "amount": 1000, # Attempted price manipulation
            "currency": "NGN",
        }
    )
    assert resp.status_code == 200
    # Backend strictly enforced ₦5,000, completely overriding attempted tampering
    assert resp.json()["amount"] == 5000.0
    assert captured_init_amount == 5000.0


# ── SALES DASHBOARD IDENTIFICATION SCENARIOS ─────────────────────────────────

@pytest.mark.asyncio
async def test_single_book_purchase_stores_exact_product_name_and_sku(test_db, monkeypatch):
    """Verify purchase of a standalone book stores exact product title and SKU."""
    monkeypatch.setattr("backend.services.email_service.send_email", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr("backend.services.meta_capi.send_purchase_event", AsyncMock(return_value={"sent": True}))
    monkeypatch.setattr("backend.workers.email_scheduler.process_email_queue", AsyncMock(return_value=0))

    ref = "ACP-QTH-TEST123"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "charge_id": "CHG_QTH",
        "email": "qth_reader@example.com",
        "name": "Alex",
        "product_slug": "quitting-the-handjob",
        "book_title": "Quitting The Handjob",
        "product_name": "Quitting The Handjob",
        "product_sku": "BOOK-QUITTING-THE-HANDJOB",
        "items": [
            {
                "product_id": "quitting-the-handjob",
                "product_sku": "BOOK-QUITTING-THE-HANDJOB",
                "name": "Quitting The Handjob",
                "quantity": 1,
                "unit_price": 5000.0,
                "total_price": 5000.0,
            }
        ],
        "base_price": 5000.0,
        "amount": 5000.0,
        "currency": "NGN",
        "payment_method": "card",
        "created_at": datetime.now(timezone.utc),
    })

    res = await complete_payment(
        test_db,
        reference=ref,
        email="qth_reader@example.com",
        name="Alex",
        amount=5000.0,
        charge_id="CHG_QTH",
        gateway_response={"status": "success", "amount": 500000},
        completed_via="webhook",
        payment_method="card",
    )
    assert res["already_completed"] is False

    payment = await test_db.payments.find_one({"reference": ref})
    assert payment is not None
    assert payment["product_name"] == "Quitting The Handjob"
    assert payment["product_sku"] == "BOOK-QUITTING-THE-HANDJOB"
    assert payment["items"][0]["name"] == "Quitting The Handjob"
    assert payment["items"][0]["product_sku"] == "BOOK-QUITTING-THE-HANDJOB"
    assert payment["items"][0]["quantity"] == 1
    assert payment["items"][0]["unit_price"] == 5000.0


@pytest.mark.asyncio
async def test_bundle_purchase_stores_academic_comeback_package_and_sku(test_db, monkeypatch):
    """Verify purchase of Academic Comeback Package stores exact bundle name and ACP-BUNDLE."""
    monkeypatch.setattr("backend.services.email_service.send_email", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr("backend.services.meta_capi.send_purchase_event", AsyncMock(return_value={"sent": True}))
    monkeypatch.setattr("backend.workers.email_scheduler.process_email_queue", AsyncMock(return_value=0))

    ref = "ACP-BUNDLE-TEST789"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "charge_id": "CHG_BUNDLE",
        "email": "bundle_buyer@example.com",
        "name": "Sarah",
        "base_price": 5000.0,
        "amount": 5000.0,
        "currency": "NGN",
        "payment_method": "bank_transfer",
        "created_at": datetime.now(timezone.utc),
    })

    res = await complete_payment(
        test_db,
        reference=ref,
        email="bundle_buyer@example.com",
        name="Sarah",
        amount=5000.0,
        charge_id="CHG_BUNDLE",
        gateway_response={"status": "success", "amount": 500000},
        completed_via="webhook",
        payment_method="bank_transfer",
    )
    assert res["already_completed"] is False

    payment = await test_db.payments.find_one({"reference": ref})
    assert payment is not None
    assert payment["product_name"] == "The Academic Comeback Package"
    assert payment["product_sku"] == "ACP-BUNDLE"
    assert payment["items"][0]["name"] == "The Academic Comeback Package"
    assert payment["items"][0]["product_sku"] == "ACP-BUNDLE"
    assert payment["items"][0]["quantity"] == 1
    assert payment["items"][0]["unit_price"] == 5000.0


def test_multi_product_order_items_formatting():
    """Verify multi-product order builds distinct line items with quantities and prices."""
    custom_items = [
        {
            "product_id": "how-to-score-high-in-any-exam",
            "sku": "BOOK-HOW-TO-SCORE-HIGH-IN-ANY-EXAM",
            "name": "How to Score High in Any Exam",
            "quantity": 2,
            "unit_price": 5000.0,
            "total_price": 10000.0,
        },
        {
            "product_id": "what-to-do-after-a-breakup",
            "sku": "BOOK-WHAT-TO-DO-AFTER-A-BREAKUP",
            "name": "What to Do After a Breakup",
            "quantity": 1,
            "unit_price": 5000.0,
            "total_price": 5000.0,
        }
    ]
    built = build_order_items(items=custom_items)
    assert len(built) == 2
    assert built[0]["name"] == "How to Score High in Any Exam"
    assert built[0]["product_sku"] == "BOOK-HOW-TO-SCORE-HIGH-IN-ANY-EXAM"
    assert built[0]["quantity"] == 2
    assert built[0]["total_price"] == 10000.0

    assert built[1]["name"] == "What to Do After a Breakup"
    assert built[1]["product_sku"] == "BOOK-WHAT-TO-DO-AFTER-A-BREAKUP"
    assert built[1]["quantity"] == 1
    assert built[1]["total_price"] == 5000.0


def test_historical_transaction_safe_resolution():
    """Verify historical transactions without 'items' resolve exact names without guessing."""
    # 1. Historical standalone book with slug
    hist_qth = {"reference": "ACP-QTH-OLD123", "amount": 5000.0, "product_slug": "quitting-the-handjob"}
    resolved_qth = resolve_payment_items(hist_qth)
    assert len(resolved_qth) == 1
    assert resolved_qth[0]["name"] == "Quitting The Handjob"
    assert resolved_qth[0]["product_sku"] == "BOOK-QUITTING-THE-HANDJOB"

    # 2. Historical book with prefix
    hist_dms = {"reference": "ACP-DMS-OLD456", "amount": 5000.0}
    resolved_dms = resolve_payment_items(hist_dms)
    assert len(resolved_dms) == 1
    assert resolved_dms[0]["name"] == "How to Close High-Paying Clients in the DMs"
    assert resolved_dms[0]["product_sku"] == "BOOK-HOW-TO-CLOSE-HIGH-PAYING-CLIENTS-IN-THE-DMS"

    # 3. Historical bundle
    hist_bundle = {"reference": "ACP-9876543210AB", "amount": 5000.0, "tier": "complete"}
    resolved_bundle = resolve_payment_items(hist_bundle)
    assert len(resolved_bundle) == 1
    assert resolved_bundle[0]["name"] == "The Academic Comeback Package"
    assert resolved_bundle[0]["product_sku"] == "ACP-BUNDLE"


@pytest.mark.asyncio
async def test_repeated_webhook_idempotency_does_not_duplicate(test_db, monkeypatch):
    """Verify repeated webhook delivery returns already_completed=True without duplicates."""
    await test_db.payments.create_index("reference", unique=True)
    monkeypatch.setattr("backend.services.email_service.send_email", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr("backend.services.meta_capi.send_purchase_event", AsyncMock(return_value={"sent": True}))
    monkeypatch.setattr("backend.workers.email_scheduler.process_email_queue", AsyncMock(return_value=0))

    ref = "ACP-IDEM-999"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "charge_id": "CHG_IDEM",
        "email": "repeat_buyer@example.com",
        "name": "Repeat Buyer",
        "amount": 5000.0,
        "currency": "NGN",
        "created_at": datetime.now(timezone.utc),
    })

    # Call 1
    res1 = await complete_payment(
        test_db,
        reference=ref,
        email="repeat_buyer@example.com",
        name="Repeat Buyer",
        amount=5000.0,
        charge_id="CHG_IDEM",
        gateway_response={"status": "success"},
        completed_via="webhook",
    )
    assert res1["already_completed"] is False

    # Call 2 (duplicate webhook)
    res2 = await complete_payment(
        test_db,
        reference=ref,
        email="repeat_buyer@example.com",
        name="Repeat Buyer",
        amount=5000.0,
        charge_id="CHG_IDEM",
        gateway_response={"status": "success"},
        completed_via="webhook",
    )
    assert res2["already_completed"] is True

    # Count payments with this reference: strictly 1
    count = await test_db.payments.count_documents({"reference": ref})
    assert count == 1


@pytest.mark.asyncio
async def test_admin_sales_api_returns_exact_product_names_and_items(client, test_db):
    """Verify GET /api/admin/analytics/sales returns exact product names, SKUs, and items."""
    admin_token = create_access_token({"sub": "admin", "email": "admin@example.com", "role": "admin"})
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Insert two test transactions
    now = datetime.now(timezone.utc)
    await test_db.payments.insert_many([
        {
            "reference": "ACP-PROD-001",
            "name": "Buyer One",
            "email": "buyer1@example.com",
            "amount": 5000.0,
            "currency": "NGN",
            "status": "success",
            "verified_at": now,
            "created_at": now,
            "product_slug": "quitting-the-handjob",
            "book_title": "Quitting The Handjob",
        },
        {
            "reference": "ACP-PROD-002",
            "name": "Buyer Two",
            "email": "buyer2@example.com",
            "amount": 5000.0,
            "currency": "NGN",
            "status": "success",
            "verified_at": now,
            "created_at": now,
            "tier": "complete",
        }
    ])

    resp = await client.get("/api/admin/analytics/sales", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    txs = data["transactions"]
    assert len(txs) >= 2

    tx_map = {t["reference"]: t for t in txs}

    # Check standalone book
    t1 = tx_map["ACP-PROD-001"]
    assert t1["product_name"] == "Quitting The Handjob"
    assert t1["product_sku"] == "BOOK-QUITTING-THE-HANDJOB"
    assert t1["items"][0]["name"] == "Quitting The Handjob"
    assert t1["items"][0]["quantity"] == 1

    # Check bundle
    t2 = tx_map["ACP-PROD-002"]
    assert t2["product_name"] == "The Academic Comeback Package"
    assert t2["product_sku"] == "ACP-BUNDLE"
    assert t2["items"][0]["name"] == "The Academic Comeback Package"
    assert t2["items"][0]["quantity"] == 1
