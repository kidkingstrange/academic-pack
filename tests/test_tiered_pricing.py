"""
Unit and Integration Tests for 3-Tier Pricing & Entitlements Architecture.
- Starter: ₦3,500 ($22)
- Complete: ₦6,000 ($35)
- VIP: ₦12,500 ($75)
"""
import pytest
from bson import ObjectId
from backend.routes.payments import compute_price_and_referral
from backend.services.payment_completion import complete_payment
from backend.routes.library import get_library
from backend.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
async def test_compute_price_and_referral_tiers(test_db):
    """Test price resolution across all tiers and currencies."""
    email = "test_student@example.com"

    # Starter tier
    amount_starter_ngn, _ = await compute_price_and_referral(test_db, email, currency="NGN", tier="starter")
    assert amount_starter_ngn == 3500.0

    amount_starter_usd, _ = await compute_price_and_referral(test_db, email, currency="USD", tier="starter")
    assert amount_starter_usd == 22.0

    # Complete tier
    amount_complete_ngn, _ = await compute_price_and_referral(test_db, email, currency="NGN", tier="complete")
    assert amount_complete_ngn == 6000.0

    amount_complete_usd, _ = await compute_price_and_referral(test_db, email, currency="USD", tier="complete")
    assert amount_complete_usd == 35.0

    # VIP tier
    amount_vip_ngn, _ = await compute_price_and_referral(test_db, email, currency="NGN", tier="vip")
    assert amount_vip_ngn == 12500.0

    amount_vip_usd, _ = await compute_price_and_referral(test_db, email, currency="USD", tier="vip")
    assert amount_vip_usd == 75.0

    # Default fallback (unspecified or unrecognized tier preserves standard sales page pricing)
    amount_default_ngn, _ = await compute_price_and_referral(test_db, email, currency="NGN", tier=None)
    assert amount_default_ngn == float(settings.PRODUCT_PRICE_NAIRA)  # ₦2,000 early-bird

    amount_unknown_ngn, _ = await compute_price_and_referral(test_db, email, currency="NGN", tier="unknown")
    assert amount_unknown_ngn == float(settings.PRODUCT_PRICE_NAIRA)  # ₦2,000 early-bird


@pytest.mark.asyncio
async def test_payment_completion_entitlements_by_tier(test_db):
    """Test that completion grants appropriate access to products based on tier."""
    # Seed 7 mock products
    prod_ids = []
    for i in range(1, 8):
        res = await test_db.products.insert_one({
            "title": f"Guide {i}",
            "description": f"Description for Guide {i}",
            "order": i,
            "is_active": True,
        })
        prod_ids.append(str(res.inserted_id))

    # 1. Test Starter Tier fulfillment
    starter_ref = "ACP-TEST-STARTER-01"
    await test_db.pending_payments.insert_one({
        "reference": starter_ref,
        "amount": 3500.0,
        "currency": "NGN",
        "tier": "starter",
    })

    await complete_payment(
        test_db,
        reference=starter_ref,
        email="starter_user@example.com",
        name="Starter Student",
        amount=3500.0,
        charge_id=1001,
        gateway_response={"status": "success"},
        completed_via="webhook",
    )

    starter_user = await test_db.users.find_one({"email": "starter_user@example.com"})
    assert starter_user is not None
    assert starter_user["tier"] == "starter"
    assert starter_user["is_vip"] is False
    assert "all" not in starter_user["purchased_products"]
    # Only books 1 and 2 should be in purchased_products
    assert set(starter_user["purchased_products"]) == {prod_ids[0], prod_ids[1]}

    # Test library route view for starter user
    lib_starter = await get_library(user=starter_user, db=test_db)
    assert lib_starter["tier"] == "starter"
    assert lib_starter["is_vip"] is False
    assert lib_starter["whatsapp_community_link"] is None

    unlocked_starter = [p for p in lib_starter["products"] if not p["locked"]]
    locked_starter = [p for p in lib_starter["products"] if p["locked"]]
    assert len(unlocked_starter) == 2
    assert len(locked_starter) == 5

    # 2. Test Complete Tier fulfillment
    complete_ref = "ACP-TEST-COMPLETE-02"
    await test_db.pending_payments.insert_one({
        "reference": complete_ref,
        "amount": 6000.0,
        "currency": "NGN",
        "tier": "complete",
    })

    await complete_payment(
        test_db,
        reference=complete_ref,
        email="complete_user@example.com",
        name="Complete Student",
        amount=6000.0,
        charge_id=1002,
        gateway_response={"status": "success"},
        completed_via="webhook",
    )

    complete_user = await test_db.users.find_one({"email": "complete_user@example.com"})
    assert complete_user is not None
    assert complete_user["tier"] == "complete"
    assert complete_user["is_vip"] is False
    assert complete_user["purchased_products"] == ["all"]

    lib_complete = await get_library(user=complete_user, db=test_db)
    assert all(not p["locked"] for p in lib_complete["products"])
    assert lib_complete["is_vip"] is False
    assert lib_complete["whatsapp_community_link"] is None

    # 3. Test VIP Tier fulfillment
    vip_ref = "ACP-TEST-VIP-03"
    await test_db.pending_payments.insert_one({
        "reference": vip_ref,
        "amount": 12500.0,
        "currency": "NGN",
        "tier": "vip",
    })

    await complete_payment(
        test_db,
        reference=vip_ref,
        email="vip_user@example.com",
        name="VIP Student",
        amount=12500.0,
        charge_id=1003,
        gateway_response={"status": "success"},
        completed_via="webhook",
    )

    vip_user = await test_db.users.find_one({"email": "vip_user@example.com"})
    assert vip_user is not None
    assert vip_user["tier"] == "vip"
    assert vip_user["is_vip"] is True
    assert vip_user["purchased_products"] == ["all"]

    lib_vip = await get_library(user=vip_user, db=test_db)
    assert all(not p["locked"] for p in lib_vip["products"])
    assert lib_vip["is_vip"] is True
    assert lib_vip["whatsapp_community_link"] is not None
