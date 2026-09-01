"""
Unit and integration tests for affiliate commission base price calculation.

Verifies that affiliate commission is strictly computed on the product's
base price (e.g. ₦5,000.00 or ₦2,000.00) rather than the gross amount
charged by Paystack which may include payment method surcharges,
bank transfer fees, or processing charges (e.g. ₦5,177.67).
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from backend.services.payment_completion import complete_payment


@pytest.mark.asyncio
async def test_commission_calculated_on_base_price_not_charged_surcharges(test_db, monkeypatch):
    """
    Exact production scenario test:
    - Base price: ₦5,000
    - Customer was charged: ₦5,177.67 (₦5,000 + ₦177.67 bank transfer fee)
    - Affiliate commission rate: 60%
    - Expected commission: ₦3,000.00 (NOT ₦3,106.60)
    """
    monkeypatch.setattr("backend.services.email_service.send_email", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr("backend.services.meta_capi.send_purchase_event", AsyncMock(return_value={"sent": True}))
    monkeypatch.setattr("backend.workers.email_scheduler.process_email_queue", AsyncMock(return_value=0))

    affiliate_code = "TESTAFF60"
    ref = "ACP-PROD-TEST-5177"
    now = datetime.now(timezone.utc)

    # 1. Seed active affiliate with 60% commission rate
    await test_db.affiliates.insert_one({
        "code": affiliate_code,
        "name": "Divine Benn-Itua",
        "email": "divine@example.com",
        "commission_percent": 60,
        "active": True,
        "created_at": now,
    })

    # 2. Seed pending payment initialized at base price of ₦5,000
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "charge_id": "CHG_5177",
        "email": "customer@example.com",
        "name": "Paying Student",
        "base_price": 5000.0,
        "amount": 5000.0,
        "currency": "NGN",
        "payment_method": "pay_with_bank",
        "referred_by": affiliate_code,
        "created_at": now,
        "split_applied": False,
    })

    # 3. Complete payment with amount_paid = 5177.67 (Paystack reported amount with fees)
    result = await complete_payment(
        test_db,
        reference=ref,
        email="customer@example.com",
        name="Paying Student",
        amount=5177.67,  # Raw amount returned from Paystack
        charge_id="CHG_5177",
        gateway_response={"status": "success", "amount": 517767},
        completed_via="webhook",
        payment_method="pay_with_bank",
    )
    assert result["already_completed"] is False

    # 4. Verify referral record
    referral = await test_db.referrals.find_one({"reference": ref})
    assert referral is not None
    assert referral["affiliate_code"] == affiliate_code
    assert referral["commission_rate"] == 60
    # Crucial assertion: 60% of 5,000 = 3,000.00 (NOT 3,106.60)
    assert referral["commission_amount"] == 3000.0
    assert referral["base_price"] == 5000.0
    assert referral["amount_charged"] == 5177.67
    assert referral["amount"] == 5000.0

    # 5. Verify payment record
    payment = await test_db.payments.find_one({"reference": ref})
    assert payment is not None
    assert payment["base_price"] == 5000.0
    assert payment["amount_charged"] == 5177.67
    assert payment["amount"] == 5000.0


@pytest.mark.asyncio
async def test_commission_method_agnostic_card_and_transfer_surcharges(test_db, monkeypatch):
    """
    Verify that whether charges are ₦5,100 (card), ₦5,250 (international/transfer),
    or promo ₦2,000 with ₦30 fee, commission is always strictly on base_price.
    """
    monkeypatch.setattr("backend.services.email_service.send_email", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr("backend.services.meta_capi.send_purchase_event", AsyncMock(return_value={"sent": True}))
    monkeypatch.setattr("backend.workers.email_scheduler.process_email_queue", AsyncMock(return_value=0))

    affiliate_code = "VARIAFF50"
    now = datetime.now(timezone.utc)

    await test_db.affiliates.insert_one({
        "code": affiliate_code,
        "name": "Variable Test Affiliate",
        "email": "var@example.com",
        "commission_percent": 50,
        "active": True,
        "created_at": now,
    })

    # Test cases: (ref, base_price, charged_amount, expected_commission)
    cases = [
        ("ACP-CARD-5100", 5000.0, 5100.0, 2500.0),
        ("ACP-USSD-5250", 5000.0, 5250.0, 2500.0),
        ("ACP-PROMO-2035", 2000.0, 2035.0, 1000.0),
    ]

    for ref, base_price, charged, expected_comm in cases:
        await test_db.pending_payments.insert_one({
            "reference": ref,
            "charge_id": f"CHG_{ref}",
            "email": f"cust_{ref}@example.com",
            "name": "Test Customer",
            "base_price": base_price,
            "amount": base_price,
            "currency": "NGN",
            "payment_method": "card",
            "referred_by": affiliate_code,
            "created_at": now,
        })

        await complete_payment(
            test_db,
            reference=ref,
            email=f"cust_{ref}@example.com",
            name="Test Customer",
            amount=charged,
            charge_id=f"CHG_{ref}",
            gateway_response={"status": "success"},
            completed_via="webhook",
        )

        ref_doc = await test_db.referrals.find_one({"reference": ref})
        assert ref_doc is not None
        assert ref_doc["base_price"] == base_price
        assert ref_doc["amount_charged"] == charged
        assert ref_doc["commission_amount"] == expected_comm
