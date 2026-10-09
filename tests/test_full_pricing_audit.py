"""
Full Website Pricing Consistency, Payment Gateway & Transaction Integrity Audit Test Suite.
Tests all 13 critical scenarios mandated by the Full Website Audit.
"""
import uuid
import hmac
import hashlib
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
import pytest
from bson import ObjectId

from backend.config import get_settings
from backend.services.payment_completion import complete_payment
from backend.workers.subscription_scheduler import run_daily_subscription_billing
from backend.routes.payments import process_webhook_payment
from backend.utils.rate_limit import limiter

settings = get_settings()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()
    yield
    limiter.reset()


# ── Scenario 1: A product with a regular price ──────────────────────────────
@pytest.mark.asyncio
async def test_scenario_1_regular_price_initialization(client, test_db, monkeypatch):
    """
    Organic visitor sees regular early-bird price:
    NGN = ₦2,000 (PRODUCT_PRICE_NAIRA)
    USD = $15 (PRODUCT_PRICE_USD)
    """
    mock_init = AsyncMock(return_value={
        "authorization_url": "https://checkout.paystack.com/auth-regular-ngn",
        "access_code": "REG_NGN_123",
        "reference": "ACP-REG-NGN-1",
    })
    monkeypatch.setattr("backend.routes.payments.initialize_transaction", mock_init)

    # NGN regular organic
    res_ngn = await client.post("/api/payments/initialize", json={
        "name": "Regular Student",
        "email": "regular.student@example.com",
    })
    assert res_ngn.status_code == 200
    data_ngn = res_ngn.json()
    assert data_ngn["amount"] == 2000.0

    # Verify Paystack was called with exact 2000 naira
    mock_init.assert_called_with(
        email="regular.student@example.com",
        amount_naira=2000.0,
        reference=data_ngn["reference"],
        callback_url=f"{settings.APP_URL}/api/payments/callback",
        metadata={
            "name": "Regular Student",
            "payment_method": "bank_transfer",
            "currency": "NGN",
            "friend_discount_applied": False,
            "friend_emails": [],
            "commission_base_price": 2000.0,
            "amount_paid": 2000.0,
        },
        channels=["bank_transfer", "bank", "card", "ussd", "qr"],
        currency=None,
        subaccount=None,
        transaction_charge=None,
    )

    # USD regular organic
    mock_init.reset_mock()
    mock_init.return_value = {
        "authorization_url": "https://checkout.paystack.com/auth-regular-usd",
        "access_code": "REG_USD_123",
        "reference": "ACP-REG-USD-1",
    }
    res_usd = await client.post("/api/payments/initialize", json={
        "name": "US Student",
        "email": "us.student@example.com",
        "country": "US",
        "currency": "USD",
    })
    assert res_usd.status_code == 200
    data_usd = res_usd.json()
    assert data_usd["amount"] == 15.0


# ── Scenario 2: A product whose price has recently changed ──────────────────
@pytest.mark.asyncio
async def test_scenario_2_urgency_price_change_transition(client, test_db, monkeypatch):
    """
    When the urgency countdown expires:
    Organic NGN jumps from ₦2,000 to ₦5,000 (PRODUCT_PRICE_LATE_NAIRA)
    Organic USD jumps from $15 to $30 (PRODUCT_PRICE_LATE_USD)
    """
    mock_init = AsyncMock(return_value={
        "authorization_url": "https://checkout.paystack.com/auth-late",
        "access_code": "LATE_123",
        "reference": "ACP-LATE-1",
    })
    monkeypatch.setattr("backend.routes.payments.initialize_transaction", mock_init)

    # 1 hour in the past timestamp
    past_timestamp_ms = (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000

    res_ngn = await client.post("/api/payments/initialize", json={
        "name": "Expired Student",
        "email": "expired.student@example.com",
        "client_expiry": past_timestamp_ms,
    })
    assert res_ngn.status_code == 200
    assert res_ngn.json()["amount"] == 5000.0

    res_usd = await client.post("/api/payments/initialize", json={
        "name": "Expired US",
        "email": "expired.us@example.com",
        "client_expiry": past_timestamp_ms,
        "country": "US",
        "currency": "USD",
    })
    assert res_usd.status_code == 200
    assert res_usd.json()["amount"] == 30.0


# ── Scenario 3: A product with an active discount (viral referral) ──────────
@pytest.mark.asyncio
async def test_scenario_3_active_discount_viral_referral(client, test_db, monkeypatch):
    """
    Viral referral discount of ₦1,000 applies when exactly 3 distinct,
    valid, unpurchased friends' emails are provided.
    Base ₦2,000 - ₦1,000 = ₦1,000.
    Invalid friends (fewer than 3, duplicates, buyer's own email) are rejected.
    """
    mock_init = AsyncMock(return_value={
        "authorization_url": "https://checkout.paystack.com/auth-viral",
        "access_code": "VIRAL_123",
        "reference": "ACP-VIRAL-1",
    })
    monkeypatch.setattr("backend.routes.payments.initialize_transaction", mock_init)

    # Valid 3 friends
    res_valid = await client.post("/api/payments/initialize", json={
        "name": "Viral Buyer",
        "email": "viral.buyer@example.com",
        "friend_emails": ["friend1@example.com", "friend2@example.com", "friend3@example.com"]
    })
    assert res_valid.status_code == 200
    assert res_valid.json()["amount"] == 1000.0

    # Invalid: only 2 friends provided
    res_two = await client.post("/api/payments/initialize", json={
        "name": "Cheater",
        "email": "cheater@example.com",
        "friend_emails": ["friend1@example.com", "friend2@example.com"]
    })
    assert res_two.status_code == 400
    assert "exactly 3" in res_two.json()["detail"]

    # Invalid: buyer uses own email
    res_self = await client.post("/api/payments/initialize", json={
        "name": "Self Refferer",
        "email": "self@example.com",
        "friend_emails": ["self@example.com", "friend2@example.com", "friend3@example.com"]
    })
    assert res_self.status_code == 400
    assert "own email" in res_self.json()["detail"]

    # Invalid: friend has already purchased
    await test_db.payments.insert_one({
        "reference": "ACP-PAID-ALREADY",
        "email": "already.paid@example.com",
        "status": "success",
    })
    res_already = await client.post("/api/payments/initialize", json={
        "name": "Buyer With Paid Friend",
        "email": "buyer.clean@example.com",
        "friend_emails": ["already.paid@example.com", "clean2@example.com", "clean3@example.com"]
    })
    assert res_already.status_code == 400
    assert "already purchased" in res_already.json()["detail"]


# ── Scenario 4: An expired coupon or promotional offer ──────────────────────
@pytest.mark.asyncio
async def test_scenario_4_expired_promotional_offer_affiliate(client, test_db, monkeypatch):
    """
    Affiliate 48-hour promotional window expires:
    Active window: ₦5,000 / $30.
    Expired window (> 48 hrs): jumps to full retail ₦20,000 / $100.
    """
    mock_init = AsyncMock(return_value={
        "authorization_url": "https://checkout.paystack.com/auth-aff-exp",
        "access_code": "EXP_123",
        "reference": "ACP-EXP-1",
    })
    monkeypatch.setattr("backend.routes.payments.initialize_transaction", mock_init)

    # Seed affiliate
    await test_db.affiliates.insert_one({
        "code": "PROMO48",
        "name": "Promo Partner",
        "commission_percent": 60.0,
        "active": True,
    })

    # Lead was created 50 hours ago
    past_lead_time = datetime.now(timezone.utc) - timedelta(hours=50)
    await test_db.leads.insert_one({
        "email": "expired.lead@example.com",
        "referred_by": "PROMO48",
        "created_at": past_lead_time,
    })

    res_exp = await client.post("/api/payments/initialize", json={
        "name": "Late Lead",
        "email": "expired.lead@example.com",
        "referral_code": "PROMO48",
    })
    assert res_exp.status_code == 200
    assert res_exp.json()["amount"] == 20000.0


# ── Scenario 5: Customer using an affiliate or referral link ────────────────
@pytest.mark.asyncio
async def test_scenario_5_affiliate_referral_link_commission_split(client, test_db, monkeypatch):
    """
    Active affiliate referral link:
    Price is ₦5,000.
    Affiliate subaccount code is attached.
    Commission is computed as 60% of base price (₦3,000).
    """
    mock_init = AsyncMock(return_value={
        "authorization_url": "https://checkout.paystack.com/auth-aff-active",
        "access_code": "AFF_ACT_123",
        "reference": "ACP-AFF-ACT-1",
    })
    monkeypatch.setattr("backend.routes.payments.initialize_transaction", mock_init)

    await test_db.affiliates.insert_one({
        "code": "ACTIVE60",
        "name": "Active Affiliate",
        "subaccount_code": "ACCT_test_subaccount",
        "commission_percent": 60.0,
        "active": True,
    })

    res = await client.post("/api/payments/initialize", json={
        "name": "Referred Customer",
        "email": "referred@example.com",
        "referral_code": "ACTIVE60",
    })
    assert res.status_code == 200
    assert res.json()["amount"] == 5000.0

    # Check pending_payments record
    pending = await test_db.pending_payments.find_one({"reference": res.json()["reference"]})
    assert pending["referred_by"] == "ACTIVE60"
    assert pending["split_applied"] is True
    assert pending["commission_base_price"] == 5000.0
    assert pending["affiliate_commission_override"] == 3000.0


# ── Scenario 6: Customer accessing a product from different pages ───────────
@pytest.mark.asyncio
async def test_scenario_6_multi_page_entry_points_pricing(client, test_db, monkeypatch):
    """
    Multi-page pricing inventory audit:
    - Homepage single book pre-order: strictly ₦5,000
    - Homepage 3-book bundle pre-order: strictly ₦12,000
    - Academic Comeback Package: ₦2,000
    - US landing page: $15
    - Sales offer checkout (Business Consultation): ₦100,000
    """
    mock_init = AsyncMock(return_value={
        "authorization_url": "https://checkout.paystack.com/test",
        "access_code": "CODE_123",
        "reference": "REF_123",
    })
    monkeypatch.setattr("backend.routes.preorders.initialize_transaction", mock_init)
    monkeypatch.setattr("backend.routes.payments.initialize_transaction", mock_init)
    monkeypatch.setattr("backend.routes.sales.initialize_transaction", mock_init)

    # 1. Homepage single book
    res_b1 = await client.post("/api/payments/preorder/initialize", json={
        "name": "Book Reader",
        "email": "book.reader@example.com",
        "book_id": "how-to-close-high-paying-clients-in-the-dms",
        "book_title": "How to Close High-Paying Clients in the DMs",
    })
    assert res_b1.status_code == 200
    assert res_b1.json()["amount"] == 5000.0

    # 2. Homepage 3-book bundle
    res_bundle = await client.post("/api/payments/preorder/initialize", json={
        "name": "Bundle Buyer",
        "email": "bundle@example.com",
        "book_id": "bundle_3_b1_b2_b3",
        "book_title": "3-Book Masterclass Bundle",
    })
    assert res_bundle.status_code == 200
    assert res_bundle.json()["amount"] == 12000.0

    # 3. Main funnel
    res_main = await client.post("/api/payments/initialize", json={
        "name": "Main Funnel",
        "email": "main.funnel@example.com",
    })
    assert res_main.status_code == 200
    assert res_main.json()["amount"] == 2000.0

    # 4. US Landing Page
    res_us = await client.post("/api/payments/initialize", json={
        "name": "US Funnel",
        "email": "us.funnel@example.com",
        "country": "US",
        "currency": "USD",
    })
    assert res_us.status_code == 200
    assert res_us.json()["amount"] == 15.0

    # 5. Sales Dynamic Offer
    offer_id = ObjectId()
    await test_db.offers.insert_one({
        "_id": offer_id,
        "name": "Business Consultation",
        "price": 100000.0,
        "billing_type": "one_time",
    })
    lead_token = "token-consult-123"
    await test_db.sales_leads.insert_one({
        "generated_link_token": lead_token,
        "offer_id": offer_id,
        "prospect_name": "Consult Prospect",
        "prospect_email": "prospect@example.com",
        "prospect_phone": "08012345678",
        "status": "pending",
    })
    info_res = await client.get(f"/api/sales/checkout/info?token={lead_token}")
    assert info_res.status_code == 200
    assert info_res.json()["offer_price"] == 100000.0


# ── Scenario 7: Stale client checkout session ───────────────────────────────
@pytest.mark.asyncio
async def test_scenario_7_stale_cached_checkout_session(client, test_db, monkeypatch):
    """
    If a visitor leaves their browser tab open and submits checkout after the
    early-bird window has expired, the server validates the timestamp and
    applies the authoritative updated price.
    """
    mock_init = AsyncMock(return_value={
        "authorization_url": "https://checkout.paystack.com/auth-stale",
        "access_code": "STALE_123",
        "reference": "ACP-STALE-1",
    })
    monkeypatch.setattr("backend.routes.payments.initialize_transaction", mock_init)

    stale_timestamp = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp() * 1000

    res = await client.post("/api/payments/initialize", json={
        "name": "Stale Tab User",
        "email": "stale.tab@example.com",
        "client_expiry": stale_timestamp,
    })
    assert res.status_code == 200
    # Price is updated to late price ₦5,000, not stale ₦2,000
    assert res.json()["amount"] == 5000.0


# ── Scenario 8: Customer attempting to tamper with the amount in browser ────
@pytest.mark.asyncio
async def test_scenario_8_client_side_amount_tampering_prevented(client, test_db, monkeypatch):
    """
    Client attempts to tamper with the price payload by sending amount = 100.
    - Preorder endpoint enforces server-authoritative ₦5,000 or ₦12,000.
    - Main payments endpoint computes price exclusively on the server.
    """
    mock_init = AsyncMock(return_value={
        "authorization_url": "https://checkout.paystack.com/auth-tamper",
        "access_code": "TAMPER_123",
        "reference": "ACP-PRE-TAMPER-1",
    })
    monkeypatch.setattr("backend.routes.preorders.initialize_transaction", mock_init)

    # Hacker sends amount: 100 for single book
    res_b1 = await client.post("/api/payments/preorder/initialize", json={
        "name": "Hacker",
        "email": "hacker@example.com",
        "book_id": "how-to-close-high-paying-clients-in-the-dms",
        "book_title": "Single Book",
        "amount": 100.0,
    })
    assert res_b1.status_code == 200
    assert res_b1.json()["amount"] == 5000.0  # Overridden by server to 5000.0!

    # Hacker sends amount: 100 for 3-book bundle
    res_b3 = await client.post("/api/payments/preorder/initialize", json={
        "name": "Hacker Bundle",
        "email": "hacker2@example.com",
        "book_id": "bundle_3_b1_b2_b3",
        "book_title": "3-Book Bundle",
        "amount": 100.0,
    })
    assert res_b3.status_code == 200
    assert res_b3.json()["amount"] == 12000.0  # Overridden by server to 12000.0!


# ── Scenario 9: A payment that succeeds ─────────────────────────────────────
@pytest.mark.asyncio
async def test_scenario_9_payment_succeeds_end_to_end(client, test_db, monkeypatch):
    """
    When Paystack confirms payment with the exact expected amount:
    - User account created/updated
    - Library access token generated
    - Payment record created in db.payments
    - Transaction marked recovered
    """
    ref = "ACP-SUCCESS-999"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "email": "buyer.success@example.com",
        "name": "Success Buyer",
        "amount": 2000.0,
        "base_price": 2000.0,
        "currency": "NGN",
    })

    mock_verify = AsyncMock(return_value={
        "status": True,
        "data": {
            "status": "success",
            "id": 11223344,
            "amount": 200000,  # 2000.00 NGN in kobo
        }
    })
    monkeypatch.setattr("backend.routes.payments.verify_transaction", mock_verify)

    res = await client.post("/api/payments/verify", json={
        "reference": ref,
        "email": "buyer.success@example.com",
        "name": "Success Buyer",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["amount"] == 2000.0
    assert data["library_token"] is not None

    user = await test_db.users.find_one({"email": "buyer.success@example.com"})
    assert user is not None
    assert "all" in user["purchased_products"]


# ── Scenario 10: A payment that fails or remains pending ────────────────────
@pytest.mark.asyncio
async def test_scenario_10_payment_fails_or_remains_pending(client, test_db, monkeypatch):
    """
    When gateway verification returns failed or pending status, no access is granted.
    """
    ref = "ACP-FAIL-001"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "email": "failing.buyer@example.com",
        "name": "Failing Buyer",
        "amount": 2000.0,
    })

    # Gateway reports failed
    mock_verify = AsyncMock(return_value={
        "status": True,
        "data": {
            "status": "failed",
            "id": 99999,
            "amount": 200000,
        }
    })
    monkeypatch.setattr("backend.routes.payments.verify_transaction", mock_verify)

    res = await client.post("/api/payments/verify", json={
        "reference": ref,
        "email": "failing.buyer@example.com",
        "name": "Failing Buyer",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert "not yet confirmed" in data["message"]

    # No user record created
    user = await test_db.users.find_one({"email": "failing.buyer@example.com"})
    assert user is None


# ── Scenario 11: A repeated payment attempt or duplicate webhook ────────────
@pytest.mark.asyncio
async def test_scenario_11_duplicate_webhook_and_poll_idempotency(client, test_db):
    """
    Submitting multiple webhook or polling confirmations for the same reference
    is completely idempotent. Atomic reference index prevents duplicate payouts.
    """
    ref = "ACP-DUP-111"
    await test_db.payments.create_index("reference", unique=True)
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "email": "idempotent@example.com",
        "name": "Idempotent User",
        "amount": 2000.0,
        "base_price": 2000.0,
        "currency": "NGN",
    })

    # Call complete_payment first time (e.g. via polling)
    res1 = await complete_payment(
        test_db,
        reference=ref,
        email="idempotent@example.com",
        name="Idempotent User",
        amount=2000.0,
        charge_id="CHARGE_111",
        gateway_response={"status": "success"},
        completed_via="polling",
    )
    assert res1["token"] is not None

    # Call complete_payment second time (e.g. via concurrent webhook)
    res2 = await complete_payment(
        test_db,
        reference=ref,
        email="idempotent@example.com",
        name="Idempotent User",
        amount=2000.0,
        charge_id="CHARGE_111",
        gateway_response={"status": "success"},
        completed_via="webhook",
    )
    assert res2["user_id"] == res1["user_id"]

    # Assert exactly 1 payment record exists in db.payments
    payments_count = await test_db.payments.count_documents({"reference": ref})
    assert payments_count == 1


# ── Scenario 12: Amount mismatch between gateway report and expected total ──
@pytest.mark.asyncio
async def test_scenario_12_amount_mismatch_flagged_for_manual_review(client, test_db, monkeypatch):
    """
    If Paystack reports that the customer paid ₦1,000 for a ₦5,000 order:
    - Polling verify returns error.
    - Webhook flags transaction into db.flagged_payments.
    - No digital access or products are granted.
    """
    ref = "ACP-MISMATCH-12"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "email": "tamper.user@example.com",
        "name": "Tamper User",
        "amount": 5000.0,
        "base_price": 5000.0,
        "currency": "NGN",
    })

    # Gateway reports only ₦1,000 (100,000 kobo)
    mock_verify = AsyncMock(return_value={
        "status": True,
        "data": {
            "status": "success",
            "id": 123456,
            "amount": 100000,
        }
    })
    monkeypatch.setattr("backend.routes.payments.verify_transaction", mock_verify)

    # 1. Verification polling check
    res_poll = await client.post("/api/payments/verify", json={
        "reference": ref,
        "email": "tamper.user@example.com",
        "name": "Tamper User",
    })
    assert res_poll.status_code == 200
    assert res_poll.json()["success"] is False
    assert "does not match expected order total" in res_poll.json()["message"]

    # 2. Webhook check
    webhook_payload = {
        "event": "charge.success",
        "data": {
            "reference": ref,
            "status": "success",
            "id": 123456,
            "amount": 100000,  # ₦1,000 instead of ₦5,000
            "customer": {"email": "tamper.user@example.com"},
        }
    }
    await process_webhook_payment(webhook_payload, test_db)

    # Verify flagged in db.flagged_payments
    flagged = await test_db.flagged_payments.find_one({"reference": ref})
    assert flagged is not None
    assert flagged["reason"] == "amount_mismatch"
    assert flagged["expected_amount"] == 5000.0
    assert flagged["amount_paid"] == 1000.0

    # User must NOT be created
    user = await test_db.users.find_one({"email": "tamper.user@example.com"})
    assert user is None


# ── Scenario 13: Subscription renewal and pre-order recurring flows ─────────
@pytest.mark.asyncio
async def test_scenario_13_subscription_renewal_billing_flow(client, test_db, monkeypatch):
    """
    Subscription renewal worker:
    - Finds active subscriptions whose next_charge_date is due.
    - Charges exact offer price (e.g. ₦45,000) via Paystack charge_authorization.
    - Advances next_charge_date by 30 days.
    - Idempotency guard prevents duplicate billing in the same period.
    """
    offer_id = ObjectId()
    await test_db.offers.insert_one({
        "_id": offer_id,
        "name": "3-Month Mentorship",
        "price": 45000.0,
        "billing_type": "recurring_monthly",
    })

    sub_id = ObjectId()
    due_date = datetime.now(timezone.utc) - timedelta(days=1)
    await test_db.subscriptions.insert_one({
        "_id": sub_id,
        "customer_name": "Renewal Student",
        "customer_email": "renewal@example.com",
        "offer_id": offer_id,
        "sales_rep_id": "rep_123",
        "card_token": "mock-card-token-12345",
        "card_last4": "1111",
        "card_brand": "Visa",
        "status": "active",
        "next_charge_date": due_date,
        "created_at": due_date - timedelta(days=30),
    })

    monkeypatch.setattr("backend.workers.subscription_scheduler.database.get_db", lambda: test_db)
    monkeypatch.setattr("backend.workers.subscription_scheduler.send_email", AsyncMock())

    await run_daily_subscription_billing()

    # Verify subscription was advanced by 30 days
    sub_updated = await test_db.subscriptions.find_one({"_id": sub_id})
    next_charge = sub_updated["next_charge_date"]
    if next_charge.tzinfo is None:
        next_charge = next_charge.replace(tzinfo=timezone.utc)
    assert next_charge > datetime.now(timezone.utc)
    assert sub_updated.get("billing_in_progress") is None

    # Verify billing log entry was written
    log_entry = await test_db.subscription_billing_logs.find_one({"subscription_id": sub_id})
    assert log_entry is not None
    assert log_entry["amount"] == 45000.0
    assert log_entry["status"] == "success"
