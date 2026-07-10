"""
Affiliate routes — admin creates affiliates; list shows click/conversion
stats. Referral attribution itself happens in payments.py (capturing the
code at checkout) and payment_completion.py (recording the conversion).
Payout/Transfers-API logic is a separate, later piece of work.
"""
import random
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from ..middleware.auth import require_admin
from ..database import get_db
from ..schemas.schemas import AffiliateCreateRequest

router = APIRouter(prefix="/api/admin/affiliates", tags=["affiliates"])


def _generate_code(name: str) -> str:
    base = "".join(ch for ch in name.upper() if ch.isalpha())[:6] or "AFF"
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{base}{suffix}"


@router.post("")
async def create_affiliate(
    body: AffiliateCreateRequest,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    now = datetime.now(timezone.utc)
    code = (body.code or "").strip().upper() or _generate_code(body.name)

    doc = {
        "code": code,
        "name": body.name,
        "email": body.email.lower(),
        "active": True,
        "created_at": now,
    }

    # Retry with a freshly generated code only if the caller didn't request
    # a specific one — a caller-specified code that collides should error,
    # not silently get a different code assigned.
    for attempt in range(5):
        try:
            result = await db.affiliates.insert_one(doc)
            break
        except DuplicateKeyError:
            if body.code:
                raise HTTPException(status_code=409, detail=f"Affiliate code '{code}' already exists")
            if attempt == 4:
                raise HTTPException(status_code=500, detail="Could not generate a unique affiliate code")
            code = _generate_code(body.name)
            doc["code"] = code

    return {
        "id": str(result.inserted_id),
        "code": code,
        "name": doc["name"],
        "email": doc["email"],
        "active": True,
        "created_at": now,
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
            "created_at": a["created_at"],
            "clicks": click_counts.get(code, 0),
            "conversions": stats.get("count", 0),
            "revenue": stats.get("revenue", 0),
        })
    return {"affiliates": out}
