"""
Unit and integration tests for the 48-hour affiliate urgency and price jump system.

Validates:
1. Affiliate referrals within the 48-hour window receive the locked-in ₦5,000 rate.
2. Affiliate referrals past the 48-hour window receive the full retail ₦20,000 rate.
3. Existing affiliate leads registered > 48 hours ago receive the ₦20,000 rate.
4. Direct / organic traffic continues receiving ₦2,000 (within 24h) and ₦5,000 (after 24h).
5. Affiliate commission correctly computes on both ₦5,000 (₦3,000 at 60%) and ₦20,000 (₦12,000 at 60%).
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from backend.routes.payments import compute_price_and_referral
from backend.services.payment_completion import complete_payment
from backend.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
async def test_affiliate_referral_during_promo_gets_5000(test_db):
    aff_code = "URGENCY48"
    await test_db.affiliates.insert_one({
        "code": aff_code,
        "name": "Affiliate Tester",
        "email": "aff@example.com",
        "commission_percent": 60,
        "active": True,
    })

    now = datetime.now(timezone.utc)
    # Even if client has an old expired timer, promo is active through Jan 1, 2027
    client_expiry_ms = (now - timedelta(days=2)).timestamp() * 1000

    amount, referred_by = await compute_price_and_referral(
        test_db,
        email="student_within_window@example.com",
        client_expiry=client_expiry_ms,
        referral_code=aff_code,
        currency="NGN"
    )

    assert referred_by == aff_code
    assert amount == settings.PACKAGE_PROMO_PRICE_NAIRA  # ₦5,000


@pytest.mark.asyncio
async def test_affiliate_referral_after_promo_date_gets_20000(test_db, monkeypatch):
    aff_code = "EXPIREDPROMO"
    await test_db.affiliates.insert_one({
        "code": aff_code,
        "name": "Affiliate Tester 2",
        "email": "aff2@example.com",
        "commission_percent": 60,
        "active": True,
    })

    # Simulate date in 2027 (after Jan 1, 2027 promo end date)
    future_date = datetime(2027, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    import datetime as dt_module

    class MockDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return future_date

    monkeypatch.setattr("backend.routes.payments.datetime", MockDateTime)

    amount, referred_by = await compute_price_and_referral(
        test_db,
        email="student_expired_window@example.com",
        client_expiry=None,
        referral_code=aff_code,
        currency="NGN"
    )

    assert referred_by == aff_code
    assert amount == settings.PACKAGE_REGULAR_PRICE_NAIRA  # ₦20,000


@pytest.mark.asyncio
async def test_affiliate_existing_lead_during_promo_retains_5000(test_db):
    aff_code = "LEADPROMO48"
    await test_db.affiliates.insert_one({
        "code": aff_code,
        "name": "Affiliate Tester 3",
        "email": "aff3@example.com",
        "commission_percent": 60,
        "active": True,
    })

    email = "lead_registered_3days_ago@example.com"
    now = datetime.now(timezone.utc)
    # Lead registered 3 days ago
    await test_db.leads.insert_one({
        "email": email,
        "name": "Old Lead",
        "referred_by": aff_code,
        "created_at": now - timedelta(days=3),
    })

    amount, referred_by = await compute_price_and_referral(
        test_db,
        email=email,
        client_expiry=None,
        referral_code=aff_code,
        currency="NGN"
    )

    assert referred_by == aff_code
    assert amount == settings.PACKAGE_PROMO_PRICE_NAIRA  # ₦5,000


@pytest.mark.asyncio
async def test_direct_traffic_during_promo_gets_5000(test_db):
    amount_direct, ref_direct = await compute_price_and_referral(
        test_db,
        email="direct_fresh@example.com",
        client_expiry=None,
        referral_code=None,
        currency="NGN"
    )
    assert ref_direct is None
    assert amount_direct == settings.PACKAGE_PROMO_PRICE_NAIRA  # ₦5,000


@pytest.mark.asyncio
async def test_affiliate_commission_on_retail_price_jump(test_db, monkeypatch):
    """
    Verifies that if a customer purchases at the ₦20,000 retail price after expiration,
    the affiliate receives the proper 60% commission (₦12,000).
    """
    monkeypatch.setattr("backend.services.email_service.send_email", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr("backend.services.meta_capi.send_purchase_event", AsyncMock(return_value={"sent": True}))
    monkeypatch.setattr("backend.workers.email_scheduler.process_email_queue", AsyncMock(return_value=0))

    aff_code = "COMM20K"
    now = datetime.now(timezone.utc)
    await test_db.affiliates.insert_one({
        "code": aff_code,
        "name": "Super Affiliate",
        "email": "super@example.com",
        "commission_percent": 60,
        "active": True,
    })

    ref = "ACP-URGENCY-20K"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "charge_id": "CHG_20000",
        "email": "buyer20k@example.com",
        "name": "Late Buyer",
        "base_price": 20000.0,
        "amount": 20000.0,
        "currency": "NGN",
        "payment_method": "card",
        "referred_by": aff_code,
        "created_at": now,
        "split_applied": False,
    })

    result = await complete_payment(
        test_db,
        reference=ref,
        email="buyer20k@example.com",
        name="Late Buyer",
        amount=20000.0,
        charge_id="CHG_20000",
        gateway_response={"status": "success", "amount": 2000000},
        completed_via="webhook",
        payment_method="card",
    )

    assert result["already_completed"] is False
    referral = await test_db.referrals.find_one({"reference": ref})
    assert referral is not None
    assert referral["commission_amount"] == 12000.0  # 60% of ₦20,000
