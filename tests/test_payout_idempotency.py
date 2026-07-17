import pytest
from datetime import datetime, timezone
from bson import ObjectId
from unittest.mock import patch, AsyncMock
from backend.services.payout_service import send_batch


@pytest.mark.asyncio
async def test_send_batch_cas_and_deterministic_reference():
    # Mock DB collections
    batch_id = str(ObjectId())
    
    mock_batch = {
        "_id": ObjectId(batch_id),
        "status": "pending_approval",
        "items": [
            {
                "affiliate_code": "TESTAFF",
                "affiliate_name": "Test Affiliate",
                "bank_code": "058",
                "account_number": "0123456789",
                "amount": 5000.0,
                "referral_ids": [ObjectId()],
                "transfer_status": "pending"
            }
        ]
    }

    mock_db = AsyncMock()
    
    # First call: CAS update returns claimed batch with status='sending'
    sending_batch = dict(mock_batch)
    sending_batch["status"] = "sending"
    mock_db.payout_batches.find_one_and_update.return_value = sending_batch
    mock_db.payout_batches.find_one.return_value = sending_batch

    with patch("backend.services.payout_service.get_ngn_balance", new_callable=AsyncMock) as mock_bal, \
         patch("backend.services.payout_service.create_transfer", new_callable=AsyncMock) as mock_transfer:
        
        mock_bal.return_value = {"status": "success", "data": {"available_balance": 100000.0}}
        mock_transfer.return_value = {"status": "success", "data": {"id": 12345}}

        res = await send_batch(mock_db, batch_id)

        # Verify CAS query structure
        call_args = mock_db.payout_batches.find_one_and_update.call_args[0][0]
        assert call_args["_id"] == ObjectId(batch_id)
        assert call_args["status"]["$in"] == ["pending_approval", "failed_partial"]

        # Verify deterministic reference
        transfer_kwargs = mock_transfer.call_args.kwargs
        assert transfer_kwargs["reference"] == f"PAYOUT{batch_id}TESTAFF"

        # Verify referral update query specifies commission_status: unpaid
        ref_update = mock_db.referrals.update_many.call_args[0][0]
        assert ref_update["commission_status"] == "unpaid"
