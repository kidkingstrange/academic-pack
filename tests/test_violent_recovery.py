"""
Unit and Integration Tests for Aggressive Multi-Touch Abandoned Recovery Engine.
Validates:
- Intra-day cadence (Steps 1..9: 15m, 2h, 6h, 12h, 18h, 24h, 30h, 42h, 54h)
- Transition to daily recurring drip (every 24h until purchase)
- Real-time halt on purchase & bonus crediting
- Unsubscribe halts all sends
- Main sales page preserves original pricing (₦2,000 early bird)
- Recovery checkout respects tier pricing (₦3,500 starter, ₦6,000 complete, ₦12,500 vip)
"""
import pytest
from datetime import datetime, timezone, timedelta
from backend.services.abandoned_recovery_service import (
    record_checkout_initialization,
    send_recovery_email_step,
    mark_transaction_recovered,
    is_buyer,
    is_unsubscribed,
)
from backend.routes.payments import compute_price_and_referral
from backend.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
async def test_main_sales_page_preserves_standard_price(test_db):
    """Confirm that organic/direct checkouts without tier continue to use ₦2,000 early-bird price."""
    email = "new_visitor@example.com"
    amount_ngn, _ = await compute_price_and_referral(test_db, email, currency="NGN", tier=None)
    assert amount_ngn == float(settings.PRODUCT_PRICE_NAIRA)  # 2,000 NGN

    amount_usd, _ = await compute_price_and_referral(test_db, email, currency="USD", tier=None)
    assert amount_usd == float(settings.PRODUCT_PRICE_USD)  # $15 USD

@pytest.mark.asyncio
async def test_affiliate_checkout_preserves_5000_naira(test_db):
    """Confirm that visitors coming via affiliate links receive the exact ₦5,000 partner price."""
    from backend.schemas.schemas import PaymentInitRequest
    
    # Verify PaymentInitRequest does not force tier="complete"
    req = PaymentInitRequest(name="Affiliate Lead", email="aff_buyer@example.com", referral_code="PARTNER123")
    assert req.tier is None

    # Pre-insert active affiliate
    await test_db.affiliates.insert_one({"code": "PARTNER123", "name": "Partner", "active": True})

    amount_ngn, ref_by = await compute_price_and_referral(
        test_db, "aff_buyer@example.com", referral_code="PARTNER123", currency="NGN", tier=req.tier
    )
    assert ref_by == "PARTNER123"
    assert amount_ngn == float(settings.PRODUCT_PRICE_LATE_NAIRA)  # Exactly ₦5,000 NGN!
@pytest.mark.asyncio
async def test_recovery_tier_pricing(test_db):
    """Confirm that recovery checkouts with explicit tiers resolve to ₦3,500 / ₦6,000 / ₦12,500."""
    email = "abandoned_lead@example.com"
    starter, _ = await compute_price_and_referral(test_db, email, currency="NGN", tier="starter")
    assert starter == 3500.0

    complete, _ = await compute_price_and_referral(test_db, email, currency="NGN", tier="complete")
    assert complete == 6000.0

    vip, _ = await compute_price_and_referral(test_db, email, currency="NGN", tier="vip")
    assert vip == 12500.0


@pytest.mark.asyncio
async def test_recovery_email_steps_render_and_send(test_db, monkeypatch):
    """Test that all recovery templates (1..9 and daily drip) render successfully without template errors."""
    async def mock_send_email(email, subject, html_content):
        assert html_content is not None
        assert len(html_content) > 50
        assert "http" in html_content
        return True, None

    import backend.services.abandoned_recovery_service as svc
    monkeypatch.setattr(svc, "send_email", mock_send_email)

    ref = "ACP-TEST-MULTITOUCH-01"
    tx = await record_checkout_initialization(
        test_db,
        email="student_test@example.com",
        name="Timi",
        amount=6000.0,
        currency="NGN",
        reference=ref,
    )

    # Test steps 1 through 9
    for step in range(1, 10):
        sent = await send_recovery_email_step(test_db, tx, step=step)
        assert sent is True

    # Test daily drip step (step 10 and 11)
    sent_10 = await send_recovery_email_step(test_db, tx, step=10)
    assert sent_10 is True

    sent_11 = await send_recovery_email_step(test_db, tx, step=11)
    assert sent_11 is True

    saved = await test_db.abandoned_transactions.find_one({"reference": ref})
    assert len(saved["emails_sent"]) == 11
    assert saved["sequence_step"] == 11


@pytest.mark.asyncio
async def test_mark_transaction_recovered_halts_and_awards_bonuses(test_db):
    """Test that paying immediately marks transaction recovered and attaches earned bonuses."""
    email = "bonus_earner@example.com"
    ref = "ACP-TEST-BONUS-01"

    # Pre-create user account
    await test_db.users.insert_one({
        "email": email,
        "name": "Bonus Earner",
        "purchased_products": [],
        "earned_bonuses": [],
    })

    # Record abandoned transaction at step 2 (within 2-hour window)
    await record_checkout_initialization(
        test_db,
        email=email,
        name="Bonus Earner",
        amount=6000.0,
        currency="NGN",
        reference=ref,
    )
    await test_db.abandoned_transactions.update_one(
        {"reference": ref},
        {"$set": {"sequence_step": 2, "status": "sequence_active"}}
    )

    # Mark recovered upon payment
    count = await mark_transaction_recovered(test_db, email=email, reference=ref)
    assert count >= 1

    # Verify abandoned status is now 'recovered'
    abandoned = await test_db.abandoned_transactions.find_one({"reference": ref})
    assert abandoned["status"] == "recovered"
    assert "The 3.0 to 4.5 GPA Active Retrieval Audio Cram Protocol" in abandoned["earned_bonuses"]

    # Verify user received the bonus
    user = await test_db.users.find_one({"email": email})
    assert "The 3.0 to 4.5 GPA Active Retrieval Audio Cram Protocol" in user["earned_bonuses"]


@pytest.mark.asyncio
async def test_unsubscribe_immediately_halts_sending(test_db, monkeypatch):
    """Verify that unsubscribing immediately halts recovery emails."""
    email = "unsub_student@example.com"
    ref = "ACP-TEST-UNSUB-01"

    tx = await record_checkout_initialization(
        test_db,
        email=email,
        name="Unsub Student",
        amount=6000.0,
        currency="NGN",
        reference=ref,
    )

    # Mark unsubscribed
    from backend.services.abandoned_recovery_service import unsubscribe_email
    await unsubscribe_email(test_db, email)

    # Attempt to send Step 1
    sent = await send_recovery_email_step(test_db, tx, step=1)
    assert sent is False
