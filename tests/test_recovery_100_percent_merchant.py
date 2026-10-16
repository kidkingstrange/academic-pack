"""
Tests for 100% Merchant Allocation on Abandoned Cart & Follow-Up Email Recovery Sales.

Policy:
When a customer abandons checkout and is recovered via follow-up emails,
recovery redirect links, or automated recovery drip, 100% of the funds go
directly to the merchant with ZERO Paystack subaccount split and ZERO affiliate commission.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from backend.services.abandoned_recovery_service import (
    record_checkout_initialization,
    send_recovery_email_step,
)
from backend.services.payment_completion import complete_payment
from backend.schemas.schemas import PaymentInitRequest


@pytest.mark.asyncio
async def test_recovery_redirect_bypasses_affiliate_and_split(client, test_db, monkeypatch):
    """
    1. Affiliate initially referred customer who abandoned.
    2. Customer receives recovery email and clicks /api/payments/recovery-redirect.
    3. New transaction must have referred_by=None and split_applied=False (100% to merchant).
    4. Upon payment completion, 0 affiliate commission is recorded.
    """
    monkeypatch.setattr("backend.services.email_service.send_email", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr("backend.services.meta_capi.send_purchase_event", AsyncMock(return_value={"sent": True}))
    monkeypatch.setattr("backend.workers.email_scheduler.process_email_queue", AsyncMock(return_value=0))
    monkeypatch.setattr("backend.routes.payments.initialize_transaction", AsyncMock(return_value={
        "authorization_url": "https://checkout.paystack.com/test-rec-auth",
        "access_code": "acc_rec_123",
        "reference": "ACP-REC-MOCK01",
    }))

    affiliate_code = "TOPPARTNER"
    await test_db.affiliates.insert_one({
        "code": affiliate_code,
        "name": "Top Partner",
        "email": "top@example.com",
        "subaccount_code": "ACCT_top123",
        "commission_percent": 60,
        "active": True,
    })

    orig_ref = "ACP-ORIG-ABANDON-01"
    email = "recovered_student@example.com"
    await record_checkout_initialization(
        test_db,
        email=email,
        name="Recovered Student",
        amount=5000.0,
        currency="NGN",
        reference=orig_ref,
        referred_by=affiliate_code,
    )

    # Simulate customer clicking recovery email link
    res = await client.get(f"/api/payments/recovery-redirect?ref={orig_ref}&tier=complete", follow_redirects=False)
    assert res.status_code == 302
    assert "paystack.com" in res.headers["location"]

    # Verify pending payment created for recovery
    pending = await test_db.pending_payments.find_one({"is_recovery": True, "email": email})
    assert pending is not None
    assert pending["referred_by"] is None  # Affiliate stripped!
    assert pending["split_applied"] is False  # 100% merchant!
    assert pending["recovery_source"] == "email_redirect"

    # Complete the recovery payment
    completion = await complete_payment(
        test_db,
        reference=pending["reference"],
        email=email,
        name="Recovered Student",
        amount=5000.0,
        charge_id="acc_rec_123",
        gateway_response={"status": "success", "amount": 500000},
        completed_via="webhook",
        payment_method="bank_transfer",
    )
    assert completion["already_completed"] is False

    # Verify zero referral commission created
    referral = await test_db.referrals.find_one({"email": email})
    assert referral is None  # No affiliate referral record!

    # Verify affiliate stats and milestone counts are strictly 0
    affiliate_refs_count = await test_db.referrals.count_documents({"affiliate_code": affiliate_code})
    assert affiliate_refs_count == 0

    from backend.services.affiliate_milestone_service import check_and_trigger_milestones
    milestone_res = await check_and_trigger_milestones(test_db, affiliate_code)
    assert milestone_res["direct_milestone_triggered"] is False
    assert milestone_res["parent_milestone_triggered"] is False

    # Verify payment recorded as recovery and 100% merchant
    payment = await test_db.payments.find_one({"reference": pending["reference"]})
    assert payment["is_recovery"] is True
    assert payment["amount"] == 6000.0


@pytest.mark.asyncio
async def test_scenario_b_returning_directly_to_website_preserves_affiliate_share(client, test_db, monkeypatch):
    """
    Scenario B: Customer who abandoned returns directly to the website on their own (not via recovery email).
    The affiliate MUST still receive their share of the money (Paystack subaccount split applied).
    """
    init_mock = AsyncMock(return_value={
        "authorization_url": "https://checkout.paystack.com/test-auth-scenario-b",
        "access_code": "acc_scenario_b_456",
        "reference": "ACP-MOCK-SCENARIO-B",
    })
    monkeypatch.setattr("backend.routes.payments.initialize_transaction", init_mock)

    affiliate_code = "PARTNER88"
    await test_db.affiliates.insert_one({
        "code": affiliate_code,
        "name": "Partner 88",
        "email": "p88@example.com",
        "subaccount_code": "ACCT_p88",
        "commission_percent": 60,
        "active": True,
    })

    email = "email_followup_buyer@example.com"
    # Insert abandoned cart created 24 hours ago
    await test_db.abandoned_transactions.insert_one({
        "reference": "ACP-ABAN-999",
        "email": email,
        "name": "Followup Buyer",
        "amount": 5000.0,
        "currency": "NGN",
        "referred_by": affiliate_code,
        "status": "sequence_active",
        "sequence_step": 3,
        "emails_sent": [{"step": 1}, {"step": 2}],
        "created_at": datetime.now(timezone.utc) - timedelta(hours=24),
    })

    # Scenario B: Customer returns directly to website without recovery flag
    init_payload = {
        "name": "Followup Buyer",
        "email": email,
        "payment_method": "bank_transfer",
        "referral_code": affiliate_code,
        "is_recovery": False,
    }
    res = await client.post("/api/payments/initialize", json=init_payload)
    assert res.status_code == 200

    # Ensure Paystack subaccount split IS applied for the affiliate in Scenario B!
    assert init_mock.called
    kwargs = init_mock.call_args.kwargs
    assert kwargs.get("subaccount") == "ACCT_p88"

    # Check pending payment doc
    pending = await test_db.pending_payments.find_one({"email": email})
    assert pending["is_recovery"] is False
    assert pending["referred_by"] == affiliate_code
    assert pending["split_applied"] is True


@pytest.mark.asyncio
async def test_scenario_a_recovery_email_link_routes_100_percent_to_merchant(client, test_db, monkeypatch):
    """
    Scenario A: Customer purchases via recovery email or with recovery flag.
    100% of the money routes to the merchant (zero affiliate split).
    """
    init_mock = AsyncMock(return_value={
        "authorization_url": "https://checkout.paystack.com/test-auth-scenario-a",
        "access_code": "acc_scenario_a_789",
        "reference": "ACP-MOCK-SCENARIO-A",
    })
    monkeypatch.setattr("backend.routes.payments.initialize_transaction", init_mock)

    affiliate_code = "PARTNER88"
    email = "recovery_email_buyer@example.com"

    # Scenario A: Customer clicked recovery link (is_recovery=True)
    init_payload = {
        "name": "Recovery Email Buyer",
        "email": email,
        "payment_method": "bank_transfer",
        "referral_code": affiliate_code,
        "is_recovery": True,
    }
    res = await client.post("/api/payments/initialize", json=init_payload)
    assert res.status_code == 200

    # Ensure NO subaccount split in Scenario A (100% to merchant)
    assert init_mock.called
    kwargs = init_mock.call_args.kwargs
    assert kwargs.get("subaccount") is None
    assert kwargs.get("transaction_charge") is None

    pending = await test_db.pending_payments.find_one({"email": email})
    assert pending["is_recovery"] is True
    assert pending["referred_by"] is None
    assert pending["split_applied"] is False


@pytest.mark.asyncio
async def test_immediate_affiliate_purchase_preserves_legitimate_commission(client, test_db, monkeypatch):
    """
    Direct, immediate affiliate conversion (no abandonment, no recovery emails)
    must continue to honor the 60% affiliate split.
    """
    init_mock = AsyncMock(return_value={
        "authorization_url": "https://checkout.paystack.com/test-auth-aff",
        "access_code": "acc_aff_789",
        "reference": "ACP-MOCK-DIRECT-AFF",
    })
    monkeypatch.setattr("backend.routes.payments.initialize_transaction", init_mock)

    affiliate_code = "LEGITAFF"
    await test_db.affiliates.insert_one({
        "code": affiliate_code,
        "name": "Legit Affiliate",
        "email": "legit@example.com",
        "subaccount_code": "ACCT_legit_sub",
        "commission_percent": 60,
        "active": True,
    })

    email = "fast_buyer@example.com"
    init_payload = {
        "name": "Fast Buyer",
        "email": email,
        "payment_method": "bank_transfer",
        "referral_code": affiliate_code,
    }
    res = await client.post("/api/payments/initialize", json=init_payload)
    assert res.status_code == 200

    # Ensure legitimate immediate sale splits with subaccount
    assert init_mock.called
    kwargs = init_mock.call_args.kwargs
    assert kwargs.get("subaccount") == "ACCT_legit_sub"

    pending = await test_db.pending_payments.find_one({"email": email})
    assert pending["referred_by"] == affiliate_code
    assert pending["split_applied"] is True
    assert pending.get("is_recovery") is False
