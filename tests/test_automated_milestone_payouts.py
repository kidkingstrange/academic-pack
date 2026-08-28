import secrets
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

from backend.services.affiliate_milestone_service import (
    check_and_trigger_milestones,
    disburse_single_milestone,
    auto_disburse_pending_milestones_for_affiliate,
    auto_disburse_all_pending_milestones,
    DIRECT_10_SALES_BONUS,
    PARENT_RECRUITER_BONUS,
)


@pytest.mark.asyncio
async def test_instant_milestone_payout_with_bank_details(test_db):
    db = test_db
    aff_code = f"AUTO_{secrets.token_hex(3).upper()}"
    aff_email = f"aff_{secrets.token_hex(4)}@example.com"
    
    # 1. Create affiliate WITH bank details
    await db.affiliates.insert_one({
        "code": aff_code,
        "name": "Chinedu Test",
        "email": aff_email,
        "bank_name": "Access Bank",
        "bank_code": "044",
        "account_number": "0123456789",
        "account_name": "Chinedu Test",
        "dashboard_token": secrets.token_urlsafe(16),
        "active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # Create 10 referral sales
    for i in range(10):
        await db.referrals.insert_one({
            "affiliate_code": aff_code,
            "reference": f"REF_{aff_code}_{i}",
            "amount": 5000.0,
            "commission_amount": 2500.0,
            "commission_status": "unpaid",
            "created_at": datetime.now(timezone.utc),
        })

    # Mock Paystack create_transfer and get_paystack_balance
    mock_transfer_resp = {
        "status": "success",
        "data": {
            "id": 123456,
            "transfer_code": "TRF_test123",
            "reference": f"MS_TEST_{aff_code}",
            "status": "success",
        }
    }
    mock_balance_resp = {
        "status": "success",
        "data": {"available_balance": 500000.0}
    }

    with patch("backend.services.affiliate_milestone_service.get_paystack_balance", AsyncMock(return_value=mock_balance_resp)), \
         patch("backend.services.affiliate_milestone_service.create_transfer", AsyncMock(return_value=mock_transfer_resp)) as mock_transfer, \
         patch("backend.services.affiliate_milestone_service.send_email", AsyncMock(return_value=True)):

        res = await check_and_trigger_milestones(db, aff_code)
        assert res["direct_milestone_triggered"] is True
        assert mock_transfer.called

        # Verify milestone in DB is marked as paid with transfer reference
        milestone = await db.affiliate_milestones.find_one({
            "affiliate_code": aff_code,
            "type": "direct_10_sales",
        })
        assert milestone is not None
        assert milestone["status"] == "paid"
        assert milestone["amount"] == DIRECT_10_SALES_BONUS
        assert milestone["transfer_code"] == "TRF_test123"
        assert milestone["paid_at"] is not None

        # Verify email was queued with is_transferred = True
        queued_email = await db.email_queue.find_one({
            "code": aff_code,
            "kind": "affiliate_direct_milestone"
        })
        assert queued_email is not None
        assert queued_email["is_transferred"] is True

    # Cleanup
    await db.affiliates.delete_one({"code": aff_code})
    await db.referrals.delete_many({"affiliate_code": aff_code})
    await db.affiliate_milestones.delete_many({"affiliate_code": aff_code})
    await db.email_queue.delete_many({"code": aff_code})


@pytest.mark.asyncio
async def test_deferred_milestone_payout_when_bank_details_added_later(test_db):
    db = test_db
    aff_code = f"DEF_{secrets.token_hex(3).upper()}"
    aff_email = f"def_{secrets.token_hex(4)}@example.com"
    
    # 1. Create affiliate WITHOUT bank details (e.g. auto-upgraded customer)
    await db.affiliates.insert_one({
        "code": aff_code,
        "name": "Ngozi Def",
        "email": aff_email,
        "bank_name": "",
        "bank_code": "",
        "account_number": "",
        "dashboard_token": secrets.token_urlsafe(16),
        "active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # Create 10 referral sales
    for i in range(10):
        await db.referrals.insert_one({
            "affiliate_code": aff_code,
            "reference": f"REF_{aff_code}_{i}",
            "amount": 5000.0,
            "commission_amount": 2500.0,
            "commission_status": "unpaid",
            "created_at": datetime.now(timezone.utc),
        })

    # Trigger milestone -> sits in 'unlocked' because no bank details
    res = await check_and_trigger_milestones(db, aff_code)
    assert res["direct_milestone_triggered"] is True

    milestone = await db.affiliate_milestones.find_one({
        "affiliate_code": aff_code,
        "type": "direct_10_sales",
    })
    assert milestone is not None
    assert milestone["status"] == "unlocked"
    assert milestone["last_error"] == "missing_bank_details"

    # 2. Affiliate adds bank details later
    await db.affiliates.update_one(
        {"code": aff_code},
        {"$set": {
            "bank_name": "Zenith Bank",
            "bank_code": "057",
            "account_number": "2088888888",
            "account_name": "Ngozi Def",
        }}
    )

    mock_transfer_resp = {
        "status": "success",
        "data": {
            "id": 987654,
            "transfer_code": "TRF_def789",
            "reference": f"MS_DEF_{aff_code}",
            "status": "success",
        }
    }
    mock_balance_resp = {
        "status": "success",
        "data": {"available_balance": 250000.0}
    }

    with patch("backend.services.affiliate_milestone_service.get_paystack_balance", AsyncMock(return_value=mock_balance_resp)), \
         patch("backend.services.affiliate_milestone_service.create_transfer", AsyncMock(return_value=mock_transfer_resp)) as mock_transfer, \
         patch("backend.services.affiliate_milestone_service.send_email", AsyncMock(return_value=True)):

        # Trigger auto-disbursement for affiliate
        disburse_results = await auto_disburse_pending_milestones_for_affiliate(db, aff_code)
        assert len(disburse_results) == 1
        assert disburse_results[0]["success"] is True

        updated_ms = await db.affiliate_milestones.find_one({"_id": milestone["_id"]})
        assert updated_ms["status"] == "paid"
        assert updated_ms["transfer_code"] == "TRF_def789"
        assert updated_ms["account_number"] == "2088888888"

    # Cleanup
    await db.affiliates.delete_one({"code": aff_code})
    await db.referrals.delete_many({"affiliate_code": aff_code})
    await db.affiliate_milestones.delete_many({"affiliate_code": aff_code})
    await db.email_queue.delete_many({"code": aff_code})


@pytest.mark.asyncio
async def test_parent_recruiter_milestone_auto_payout(test_db):
    db = test_db
    parent_code = f"PARENT_{secrets.token_hex(3).upper()}"
    recruit_code = f"RECRUIT_{secrets.token_hex(3).upper()}"
    
    # 1. Create parent affiliate with bank details
    await db.affiliates.insert_one({
        "code": parent_code,
        "name": "Senior Recruiter",
        "email": f"parent_{secrets.token_hex(4)}@example.com",
        "bank_name": "GTBank",
        "bank_code": "058",
        "account_number": "0112233445",
        "account_name": "Senior Recruiter",
        "dashboard_token": secrets.token_urlsafe(16),
        "active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # 2. Create recruited affiliate with parent_code
    await db.affiliates.insert_one({
        "code": recruit_code,
        "name": "Junior Seller",
        "email": f"recruit_{secrets.token_hex(4)}@example.com",
        "invited_by": parent_code,
        "bank_name": "UBA",
        "bank_code": "033",
        "account_number": "2033445566",
        "account_name": "Junior Seller",
        "dashboard_token": secrets.token_urlsafe(16),
        "active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # Create 10 sales for recruit
    for i in range(10):
        await db.referrals.insert_one({
            "affiliate_code": recruit_code,
            "reference": f"REF_{recruit_code}_{i}",
            "amount": 5000.0,
            "commission_amount": 2500.0,
            "commission_status": "unpaid",
            "created_at": datetime.now(timezone.utc),
        })

    mock_transfer_resp = {
        "status": "success",
        "data": {
            "id": 555555,
            "transfer_code": "TRF_parent555",
            "reference": f"MS_PAR_{parent_code}",
            "status": "success",
        }
    }
    mock_balance_resp = {
        "status": "success",
        "data": {"available_balance": 1000000.0}
    }

    with patch("backend.services.affiliate_milestone_service.get_paystack_balance", AsyncMock(return_value=mock_balance_resp)), \
         patch("backend.services.affiliate_milestone_service.create_transfer", AsyncMock(return_value=mock_transfer_resp)), \
         patch("backend.services.affiliate_milestone_service.send_email", AsyncMock(return_value=True)):

        res = await check_and_trigger_milestones(db, recruit_code)
        assert res["direct_milestone_triggered"] is True
        assert res["parent_milestone_triggered"] is True

        # Verify parent recruiter milestone in DB is paid
        parent_milestone = await db.affiliate_milestones.find_one({
            "affiliate_code": parent_code,
            "type": "referral_subaffiliate_10_sales",
        })
        assert parent_milestone is not None
        assert parent_milestone["status"] == "paid"
        assert parent_milestone["amount"] == PARENT_RECRUITER_BONUS
        assert parent_milestone["account_number"] == "0112233445"

    # Cleanup
    await db.affiliates.delete_many({"code": {"$in": [parent_code, recruit_code]}})
    await db.referrals.delete_many({"affiliate_code": recruit_code})
    await db.affiliate_milestones.delete_many({"affiliate_code": {"$in": [parent_code, recruit_code]}})
    await db.email_queue.delete_many({"code": {"$in": [parent_code, recruit_code]}})
