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


async def sync_pending_batch(db, batch: dict) -> dict:
    """Dynamically sync a pending/failed_partial batch with current unpaid referrals to ensure up-to-date figures."""
    if batch["status"] not in ("pending_approval", "failed_partial"):
        return batch

    # Fetch all unpaid referrals in the system
    referrals = await db.referrals.find({"commission_status": "unpaid"}).to_list(10000)
    
    by_affiliate = {}
    for r in referrals:
        by_affiliate.setdefault(r["affiliate_code"], []).append(r)

    # Bulk fetch all required affiliates at once to eliminate N+1 loop
    codes = list(by_affiliate.keys())
    affiliates_list = await db.affiliates.find({"code": {"$in": codes}}).to_list(len(codes))
    affiliates_map = {a["code"]: a for a in affiliates_list}

    items = []
    total_amount = 0.0
    existing_items_map = {i["affiliate_code"]: i for i in batch.get("items", [])}

    for code, refs in by_affiliate.items():
        affiliate = affiliates_map.get(code)
        if not affiliate:
            continue

        amount = round(sum(r.get("commission_amount", 0) or 0 for r in refs), 2)
        bank_code = (affiliate.get("bank_code") or "").strip()
        
        existing = existing_items_map.get(code)
        if existing and existing.get("amount") == amount:
            transfer_status = existing.get("transfer_status", "pending")
            flw_transfer_id = existing.get("flw_transfer_id")
            error = existing.get("error")
        else:
            transfer_status = "pending" if bank_code else "blocked_missing_bank_code"
            flw_transfer_id = None
            error = None

        items.append({
            "affiliate_code": code,
            "affiliate_name": affiliate.get("name", ""),
            "bank_name": affiliate.get("bank_name", ""),
            "bank_code": bank_code,
            "account_number": affiliate.get("account_number", ""),
            "account_name": affiliate.get("account_name", ""),
            "amount": amount,
            "referral_ids": [r["_id"] for r in refs],
            "transfer_status": transfer_status,
            "flw_transfer_id": flw_transfer_id,
            "error": error,
        })
        total_amount += amount

    # Update the batch document in MongoDB
    await db.payout_batches.update_one(
        {"_id": batch["_id"]},
        {"$set": {
            "items": items,
            "total_amount": round(total_amount, 2)
        }}
    )
    batch["items"] = items
    batch["total_amount"] = round(total_amount, 2)
    return batch


@router.get("/batches")
async def list_batches(limit: int = 20, current_user=Depends(require_admin), db=Depends(get_db)):
    batches = await db.payout_batches.find().sort("created_at", -1).to_list(limit)
    synced_batches = []
    for b in batches:
        if b["status"] in ("pending_approval", "failed_partial"):
            b = await sync_pending_batch(db, b)
        synced_batches.append(_serialize_batch(b))
    return {"batches": synced_batches}


@router.get("/batches/{batch_id}")
async def get_batch(batch_id: str, current_user=Depends(require_admin), db=Depends(get_db)):
    batch = await db.payout_batches.find_one({"_id": ObjectId(batch_id)})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch["status"] in ("pending_approval", "failed_partial"):
        batch = await sync_pending_batch(db, batch)
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
        batch = await db.payout_batches.find_one({"_id": ObjectId(batch_id)})
        if batch and batch["status"] in ("pending_approval", "failed_partial"):
            await sync_pending_batch(db, batch)
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


@router.delete("/batches/{batch_id}")
async def discard_batch(batch_id: str, current_user=Depends(require_admin), db=Depends(get_db)):
    """Discard a pending or failed payout batch so it can be rebuilt."""
    try:
        oid = ObjectId(batch_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid batch ID format")

    batch = await db.payout_batches.find_one({"_id": oid})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    if batch["status"] not in ("pending_approval", "failed_partial"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete a batch that has already been {batch['status']}"
        )

    # Delete the batch document
    await db.payout_batches.delete_one({"_id": oid})
    return {"status": "ok", "message": "Batch discarded successfully"}
