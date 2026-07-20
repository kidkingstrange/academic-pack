import pytest
from datetime import datetime, timezone
from bson import ObjectId
from unittest.mock import patch, AsyncMock
from backend.workers.subscription_scheduler import run_daily_subscription_billing


@pytest.mark.asyncio
async def test_subscription_idempotency_claim_and_reference():
    sub_id = ObjectId()
    offer_id = ObjectId()
    now = datetime(2026, 7, 17, 12, 0, 0, tzinfo=timezone.utc)

    mock_sub = {
        "_id": sub_id,
        "offer_id": offer_id,
        "card_token": "flw-token-123",
        "customer_email": "sub@example.com",
        "customer_name": "Jane Sub",
        "next_charge_date": now,
        "status": "active"
    }
    mock_offer = {
        "_id": offer_id,
        "name": "Academic Comeback Monthly",
        "price": 10000.0
    }

    from unittest.mock import MagicMock
    mock_db = AsyncMock()
    mock_find_cursor = MagicMock()
    mock_find_cursor.to_list = AsyncMock(return_value=[mock_sub])
    mock_db.subscriptions.find = MagicMock(return_value=mock_find_cursor)
    mock_db.offers.find = MagicMock(return_value=MagicMock(to_list=AsyncMock(return_value=[mock_offer])))
    mock_db.subscriptions.find_one_and_update.return_value = mock_sub
    mock_db.offers.find_one.return_value = mock_offer

    with patch("backend.workers.subscription_scheduler.database.get_db", return_value=mock_db), \
         patch("backend.workers.subscription_scheduler.charge_authorization", new_callable=AsyncMock) as mock_charge, \
         patch("backend.workers.subscription_scheduler.send_email", AsyncMock()):

        mock_charge.return_value = {"status": True, "data": {"status": "success", "amount": 1000000}}

        await run_daily_subscription_billing()

        # Check atomic claim call
        claim_call = mock_db.subscriptions.find_one_and_update.call_args[0][0]
        assert claim_call["_id"] == sub_id
        assert claim_call["status"] == "active"
        assert claim_call["billing_in_progress"] == {"$ne": True}

        # Check deterministic reference
        charge_kwargs = mock_charge.call_args.kwargs
        assert charge_kwargs["reference"] == f"SUB-REN-{sub_id}-20260717"
