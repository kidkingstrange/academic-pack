"""
Affiliate-facing read-only stats — no password, just their private
dashboard_token (distinct from their public referral `code`, which is
shared everywhere in links and can never double as a login credential).

Returns only what an affiliate needs to see about themselves: their own
clicks, conversions, revenue, commission rate, and what's been paid vs
still owed. No other affiliate's data is ever reachable through this.
"""
from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db

router = APIRouter(prefix="/api/affiliate", tags=["affiliate-dashboard"])


@router.get("/me")
async def get_my_stats(token: str, db=Depends(get_db)):
    affiliate = await db.affiliates.find_one({"dashboard_token": token})
    if not affiliate:
        raise HTTPException(status_code=401, detail="Invalid dashboard link")

    code = affiliate["code"]
    clicks = await db.referral_clicks.count_documents({"affiliate_code": code})

    referrals = await db.referrals.find(
        {"affiliate_code": code}
    ).sort("created_at", -1).to_list(1000)

    revenue = sum(r.get("amount", 0) or 0 for r in referrals)
    commission_earned = sum(r.get("commission_amount", 0) or 0 for r in referrals)
    commission_paid = sum(
        r.get("commission_amount", 0) or 0 for r in referrals if r.get("commission_status") == "paid"
    )

    sales = [
        {
            "date": r["created_at"],
            "amount": r.get("amount", 0),
            "commission_amount": r.get("commission_amount", 0),
            "status": r.get("commission_status", "unpaid"),
        }
        for r in referrals
    ]

    return {
        "code": code,
        "name": affiliate["name"],
        "active": affiliate.get("active", True),
        "commission_percent": affiliate.get("commission_percent", 0),
        "clicks": clicks,
        "conversions": len(referrals),
        "revenue": revenue,
        "commission_earned": commission_earned,
        "commission_paid": commission_paid,
        "commission_owed": commission_earned - commission_paid,
        "sales": sales,
    }
