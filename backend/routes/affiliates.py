"""
Admin-side affiliate routes — create affiliates directly, list them with
click/conversion stats, deactivate one. The public self-registration
flow lives in routes/affiliate_public.py; both share the same creation
logic via services/affiliate_service.py.

Referral attribution itself happens in payments.py (capturing the code
at checkout) and payment_completion.py (recording the conversion).
Payout/Transfers-API logic is a separate, later piece of work.
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..middleware.auth import require_admin
from ..database import get_db
from ..schemas.schemas import AffiliateCreateRequest
from ..services.affiliate_service import create_affiliate_record

router = APIRouter(prefix="/api/admin/affiliates", tags=["affiliates"])


@router.post("")
async def create_affiliate(
    body: AffiliateCreateRequest,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    try:
        affiliate = await create_affiliate_record(
            db,
            name=body.name,
            email=body.email,
            source="admin_created",
            code=body.code,
        )
    except ValueError as e:
        reason = str(e)
        if reason == "duplicate_email":
            raise HTTPException(status_code=409, detail="An affiliate with this email already exists")
        if reason == "duplicate_code":
            raise HTTPException(status_code=409, detail=f"Affiliate code '{body.code}' already exists")
        raise HTTPException(status_code=500, detail="Could not generate a unique affiliate code")

    return {
        "id": affiliate["id"],
        "code": affiliate["code"],
        "name": affiliate["name"],
        "email": affiliate["email"],
        "active": True,
        "source": "admin_created",
        "created_at": affiliate["created_at"],
        "clicks": 0,
        "conversions": 0,
        "revenue": 0,
    }


@router.get("")
async def list_affiliates(current_user=Depends(require_admin), db=Depends(get_db)):
    affiliates = await db.affiliates.find({}).sort("created_at", -1).to_list(500)

    click_counts = {
        row["_id"]: row["count"]
        for row in await db.referral_clicks.aggregate([
            {"$group": {"_id": "$affiliate_code", "count": {"$sum": 1}}}
        ]).to_list(500)
    }
    referral_stats = {
        row["_id"]: row
        for row in await db.referrals.aggregate([
            {"$group": {"_id": "$affiliate_code", "count": {"$sum": 1}, "revenue": {"$sum": "$amount"}}}
        ]).to_list(500)
    }

    out = []
    for a in affiliates:
        code = a["code"]
        stats = referral_stats.get(code, {})
        out.append({
            "id": str(a["_id"]),
            "code": code,
            "name": a["name"],
            "email": a["email"],
            "active": a.get("active", True),
            "source": a.get("source", "admin_created"),
            "created_at": a["created_at"],
            "clicks": click_counts.get(code, 0),
            "conversions": stats.get("count", 0),
            "revenue": stats.get("revenue", 0),
        })
    return {"affiliates": out}


@router.post("/{affiliate_id}/deactivate")
async def deactivate_affiliate(
    affiliate_id: str,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    """
    Immediately stops new attribution: /r/{code} and checkout's referral
    validation both filter on active=True already, so flipping this flag
    is sufficient — no other code path needs to change. Existing unpaid
    conversions are flagged for manual review, never deleted, and any
    future payout run should skip anything not still "unpaid".
    """
    try:
        affiliate = await db.affiliates.find_one({"_id": ObjectId(affiliate_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid affiliate id")
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")

    now = datetime.now(timezone.utc)
    await db.affiliates.update_one(
        {"_id": affiliate["_id"]},
        {"$set": {"active": False, "deactivated_at": now}},
    )
    flagged = await db.referrals.update_many(
        {"affiliate_code": affiliate["code"], "payout_status": "unpaid"},
        {"$set": {"payout_status": "flagged_for_review", "flagged_at": now}},
    )
    return {"success": True, "flagged_conversions": flagged.modified_count}
