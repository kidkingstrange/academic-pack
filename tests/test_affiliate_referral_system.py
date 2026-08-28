"""
End-to-end tests for the 2-Tier Affiliate Referral System:
- Affiliate registration with recruiter tracking (`invited_by`)
- Direct 10-sale milestone bonus (₦10,000 cash bonus to seller)
- Parent recruiter referral bonus (₦5,000 cash bonus to recruiter when recruit hits 10 sales)
- Idempotency & duplicate protection on milestone triggers
- Dashboard stats, recruited affiliates tracking, and milestone earnings API
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from backend.services.affiliate_milestone_service import (
    check_and_trigger_milestones, get_affiliate_recruits_and_bonuses,
    MILESTONE_SALES_TARGET, DIRECT_10_SALES_BONUS, PARENT_RECRUITER_BONUS
)
from backend.services.payment_completion import complete_payment


async def _simulate_sale(db, affiliate_code: str, index: int):
    ref_id = f"PAY_REF_{affiliate_code}_{index}"
    now = datetime.now(timezone.utc)
    await db.pending_payments.insert_one({
        "reference": ref_id,
        "email": f"customer_{index}_{affiliate_code.lower()}@example.com",
        "name": f"Customer {index}",
        "amount": 10000.0,
        "referred_by": affiliate_code,
        "created_at": now,
    })
    return await complete_payment(
        db,
        reference=ref_id,
        email=f"customer_{index}_{affiliate_code.lower()}@example.com",
        name=f"Customer {index}",
        amount=10000.0,
        charge_id=f"CHG_{index}",
        gateway_response={"status": "success"},
        completed_via="webhook",
    )


@pytest.mark.asyncio
async def test_affiliate_registration_with_recruiter_and_invite_links(client, test_db, monkeypatch):
    """Register parent affiliate A, then recruit affiliate B via A's invite link."""
    monkeypatch.setattr("backend.services.email_service.send_email", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr("backend.services.meta_capi.send_complete_registration_event", AsyncMock(return_value={"sent": True}))
    monkeypatch.setattr("backend.workers.email_scheduler.process_email_queue", AsyncMock(return_value=0))

    # 1. Register Parent Affiliate A
    res_a = await client.post("/api/affiliates/register", json={
        "name": "Recruiter Alpha",
        "email": "alpha@example.com",
        "bank_name": "Access Bank",
        "account_number": "0123456789",
        "account_name": "Recruiter Alpha",
    })
    assert res_a.status_code == 200
    data_a = res_a.json()
    code_a = data_a["code"]
    token_a = data_a["dashboard_link"].split("token=")[-1]
    assert "affiliate_invite_link" in data_a
    assert f"invite={code_a}" in data_a["affiliate_invite_link"]

    # 2. Register Sub-Affiliate B with invited_by = code_a
    res_b = await client.post("/api/affiliates/register", json={
        "name": "Seller Beta",
        "email": "beta@example.com",
        "bank_name": "GTBank",
        "account_number": "0987654321",
        "account_name": "Seller Beta",
        "invited_by": code_a,
    })
    assert res_b.status_code == 200
    data_b = res_b.json()
    code_b = data_b["code"]
    token_b = data_b["dashboard_link"].split("token=")[-1]

    # Verify B has invited_by recorded in DB
    aff_b_doc = await test_db.affiliates.find_one({"code": code_b})
    assert aff_b_doc["invited_by"] == code_a

    # Check welcome emails were queued
    queued_welcome = await test_db.email_queue.find({"kind": "affiliate_welcome"}).to_list(10)
    assert len(queued_welcome) == 2


@pytest.mark.asyncio
async def test_10_sales_milestone_and_recruiter_bonus_trigger(client, test_db, monkeypatch):
    """Simulate 10 sales for sub-affiliate B and verify both bonuses trigger once."""
    monkeypatch.setattr("backend.services.email_service.send_email", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr("backend.services.payment_completion.send_purchase_event", AsyncMock(return_value={"sent": True}))
    monkeypatch.setattr("backend.services.payment_completion.process_email_queue", AsyncMock(return_value=0))
    monkeypatch.setattr("backend.services.payment_completion.enqueue_sequence_for_subscriber", AsyncMock(return_value=0))
    monkeypatch.setattr("backend.services.meta_capi.send_complete_registration_event", AsyncMock(return_value={"sent": True}))
    monkeypatch.setattr("backend.workers.email_scheduler.process_email_queue", AsyncMock(return_value=0))

    # Setup Parent A and Sub-Affiliate B
    res_a = await client.post("/api/affiliates/register", json={
        "name": "Recruiter A",
        "email": "recruiter_a@example.com",
        "bank_name": "Access Bank",
        "account_number": "0123456781",
        "account_name": "Recruiter A",
    })
    code_a = res_a.json()["code"]
    token_a = res_a.json()["dashboard_link"].split("token=")[-1]

    res_b = await client.post("/api/affiliates/register", json={
        "name": "Seller B",
        "email": "seller_b@example.com",
        "bank_name": "Zenith Bank",
        "account_number": "0123456782",
        "account_name": "Seller B",
        "invited_by": code_a,
    })
    code_b = res_b.json()["code"]
    token_b = res_b.json()["dashboard_link"].split("token=")[-1]

    # 1. Simulate 9 sales for B
    for i in range(1, 10):
        await _simulate_sale(test_db, code_b, i)

    # Check milestone bonus count after 9 sales (should be 0)
    bonuses_after_9 = await test_db.affiliate_milestones.count_documents({})
    assert bonuses_after_9 == 0

    # Check B's dashboard before 10th sale
    dash_b_9 = (await client.get(f"/api/affiliate/me?token={token_b}")).json()
    assert dash_b_9["conversions"] == 9
    assert dash_b_9["direct_milestone_unlocked"] is False
    assert dash_b_9["direct_milestone_progress"] == 90.0
    assert len(dash_b_9["milestones"]) == 0

    # 2. Simulate 10th sale for B
    await _simulate_sale(test_db, code_b, 10)

    # Verify Milestone Documents created
    # Bonus 1: Seller B gets ₦10,000 direct milestone
    bonus_b = await test_db.affiliate_milestones.find_one({
        "affiliate_code": code_b,
        "type": "direct_10_sales",
    })
    assert bonus_b is not None
    assert bonus_b["amount"] == DIRECT_10_SALES_BONUS
    assert bonus_b["sales_count"] == 10
    assert bonus_b["status"] == "unlocked"

    # Bonus 2: Parent A gets ₦5,000 recruiter referral bonus
    bonus_a = await test_db.affiliate_milestones.find_one({
        "affiliate_code": code_a,
        "type": "referral_subaffiliate_10_sales",
        "subaffiliate_code": code_b,
    })
    assert bonus_a is not None
    assert bonus_a["amount"] == PARENT_RECRUITER_BONUS
    assert bonus_a["status"] == "unlocked"

    # Verify notification emails were queued
    direct_email = await test_db.email_queue.find_one({"kind": "affiliate_direct_milestone"})
    assert direct_email is not None
    assert direct_email["code"] == code_b
    assert direct_email["bonus_amount"] == DIRECT_10_SALES_BONUS

    parent_email = await test_db.email_queue.find_one({"kind": "affiliate_parent_referral_bonus"})
    assert parent_email is not None
    assert parent_email["code"] == code_a
    assert parent_email["bonus_amount"] == PARENT_RECRUITER_BONUS

    # 3. Verify Idempotency on 11th and 12th sales
    for i in (11, 12):
        await _simulate_sale(test_db, code_b, i)

    # Total milestone documents in DB must remain exactly 2
    total_bonuses = await test_db.affiliate_milestones.count_documents({})
    assert total_bonuses == 2

    # 4. Check Dashboards
    # Check Seller B Dashboard
    dash_b = (await client.get(f"/api/affiliate/me?token={token_b}")).json()
    assert dash_b["conversions"] == 12
    assert dash_b["direct_milestone_unlocked"] is True
    assert dash_b["direct_milestone_progress"] == 100.0
    assert dash_b["total_bonus_unlocked"] == DIRECT_10_SALES_BONUS
    assert len(dash_b["milestones"]) == 1
    assert dash_b["milestones"][0]["type"] == "direct_10_sales"

    # Check Parent A Dashboard
    dash_a = (await client.get(f"/api/affiliate/me?token={token_a}")).json()
    assert dash_a["total_recruits"] == 1
    assert len(dash_a["invited_affiliates"]) == 1
    recruit_b_info = dash_a["invited_affiliates"][0]
    assert recruit_b_info["code"] == code_b
    assert recruit_b_info["sales_count"] == 12
    assert recruit_b_info["bonus_unlocked"] is True
    assert dash_a["total_bonus_unlocked"] == PARENT_RECRUITER_BONUS
    assert len(dash_a["milestones"]) == 1
    assert dash_a["milestones"][0]["type"] == "referral_subaffiliate_10_sales"
