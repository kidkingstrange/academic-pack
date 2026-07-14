"""
Admin-only endpoints for the biweekly affiliate payout batches and the
owner's own settlement withdrawal. Every endpoint that can move money
requires an explicit admin action — nothing here fires automatically.
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from ..middleware.auth import require_admin
from ..services.payout_service import (
    build_pending_batch,
    get_settlement_summary,
    send_batch,
    withdraw_settlement_share,
)

router = APIRouter(prefix="/api/admin/payouts", tags=["admin-payouts"])


def _serialize_batch(batch: dict) -> dict:
    batch = dict(batch)
    batch["id"] = str(batch.pop("_id"))
    for item in batch.get("items", []):
        item["referral_ids"] = [str(r) for r in item.get("referral_ids", [])]
    return batch


@router.get("/batches")
async def list_batches(limit: int = 20, current_user=Depends(require_admin), db=Depends(get_db)):
    batches = await db.payout_batches.find().sort("created_at", -1).to_list(limit)
    return {"batches": [_serialize_batch(b) for b in batches]}


@router.get("/batches/{batch_id}")
async def get_batch(batch_id: str, current_user=Depends(require_admin), db=Depends(get_db)):
    batch = await db.payout_batches.find_one({"_id": ObjectId(batch_id)})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _serialize_batch(batch)


@router.post("/build-now")
async def build_now(current_user=Depends(require_admin), db=Depends(get_db)):
    """
    Manually build a batch off the biweekly cycle — e.g. to review what's
    currently owed without waiting for the 1st/15th. Never sends money.
    """
    now = datetime.now(timezone.utc)
    last_batch = await db.payout_batches.find_one(sort=[("created_at", -1)])
    period_start = last_batch["created_at"] if last_batch else now
    batch = await build_pending_batch(db, period_start=period_start, period_end=now)
    if not batch:
        return {"status": "ok", "message": "Nothing currently owed to any affiliate", "batch": None}
    return {"status": "ok", "batch": _serialize_batch(batch)}


@router.post("/batches/{batch_id}/approve")
async def approve_batch(batch_id: str, current_user=Depends(require_admin), db=Depends(get_db)):
    """
    Send every sendable item in the batch. Partial failures are normal —
    the response reflects exactly what succeeded, failed, or was blocked.
    """
    try:
        batch = await send_batch(db, batch_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _serialize_batch(batch)


@router.get("/settlement")
async def settlement_summary(current_user=Depends(require_admin), db=Depends(get_db)):
    """What's actually yours to withdraw right now."""
    try:
        return await get_settlement_summary(db)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/settlement/withdraw")
async def settlement_withdraw(payload: dict, current_user=Depends(require_admin), db=Depends(get_db)):
    """
    Transfer part or all of your available share to the configured
    settlement bank account. Amount is explicit and admin-chosen — never
    auto-computed and sent without this endpoint being called directly.
    """
    amount = payload.get("amount")
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be a positive number")

    summary = await get_settlement_summary(db)
    if amount > summary["available_to_withdraw"]:
        raise HTTPException(
            status_code=400,
            detail=f"Requested ₦{amount:,.2f} exceeds available ₦{summary['available_to_withdraw']:,.2f}",
        )

    try:
        record = await withdraw_settlement_share(db, amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record["id"] = str(record.pop("_id"))
    return record
