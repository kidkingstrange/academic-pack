import secrets
import pytest
from datetime import datetime, timezone
from backend.services.affiliate_service import get_or_create_customer_affiliate
from backend.services.payment_completion import complete_payment

@pytest.mark.asyncio
async def test_get_or_create_customer_affiliate_idempotent(test_db):
    db = test_db
    test_email = f"buyer_test_{secrets.token_hex(4)}@example.com"
    test_name = "Emeka Okonkwo"
    
    # 1. First call: provisions new affiliate
    aff_doc, was_created = await get_or_create_customer_affiliate(
        db,
        name=test_name,
        email=test_email,
    )
    assert was_created is True
    assert aff_doc["email"] == test_email
    assert aff_doc["source"] == "auto_customer_upgrade"
    assert aff_doc["code"].startswith("EMEKA") or len(aff_doc["code"]) >= 6
    assert aff_doc["dashboard_token"] is not None
    assert aff_doc["active"] is True
    
    # 2. Second call: finds existing affiliate
    aff_doc_2, was_created_2 = await get_or_create_customer_affiliate(
        db,
        name=test_name,
        email=test_email,
    )
    assert was_created_2 is False
    assert aff_doc_2["code"] == aff_doc["code"]
    assert aff_doc_2["email"] == test_email
    
    # Cleanup
    await db.affiliates.delete_one({"email": test_email})


@pytest.mark.asyncio
async def test_payment_completion_auto_provisions_customer_as_affiliate(test_db):
    db = test_db
    test_email = f"auto_buyer_{secrets.token_hex(4)}@example.com"
    test_name = "Chidinma Nwosu"
    test_ref = f"ACP-TEST-{secrets.token_hex(4).upper()}"
    
    # Create pending payment
    await db.pending_payments.insert_one({
        "reference": test_ref,
        "email": test_email,
        "name": test_name,
        "amount": 5000.0,
        "currency": "NGN",
        "created_at": datetime.now(timezone.utc),
    })
    
    # Execute payment completion
    result = await complete_payment(
        db,
        reference=test_ref,
        email=test_email,
        name=test_name,
        amount=5000.0,
        charge_id="CHG_TEST",
        gateway_response={"status": "success"},
        completed_via="webhook",
    )
    
    # Verify affiliate was provisioned in db.affiliates
    aff = await db.affiliates.find_one({"email": test_email})
    assert aff is not None
    assert aff["name"] == test_name
    assert aff["source"] == "auto_customer_upgrade"
    assert aff["active"] is True
    
    # Verify welcome email was queued with affiliate links
    queued_welcome = await db.email_queue.find_one({"email": test_email, "kind": "welcome"})
    assert queued_welcome is not None
    assert queued_welcome["affiliate_code"] == aff["code"]
    assert f"?ref={aff['code']}" in queued_welcome["referral_link"]
    assert f"?invite={aff['code']}" in queued_welcome["recruiter_link"]
    
    # Cleanup
    await db.affiliates.delete_one({"email": test_email})
    await db.users.delete_one({"email": test_email})
    await db.payments.delete_one({"reference": test_ref})
    await db.subscribers.delete_one({"email": test_email})
    await db.email_queue.delete_many({"email": test_email})
    await db.pending_payments.delete_one({"reference": test_ref})

