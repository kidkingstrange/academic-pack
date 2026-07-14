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

    # No customer name/email here deliberately — affiliates see that a
    # sale happened and what they earned from it, never who the customer
    # was. Keep this list to date + amount only.
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
        "email": affiliate.get("email", ""),
        "bank_name": affiliate.get("bank_name", ""),
        "account_number": affiliate.get("account_number", ""),
        "account_name": affiliate.get("account_name", ""),
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


@router.post("/bank-details")
async def update_my_bank_details(token: str, body: dict, db=Depends(get_db)):
    affiliate = await db.affiliates.find_one({"dashboard_token": token})
    if not affiliate:
        raise HTTPException(status_code=401, detail="Invalid dashboard link")

    bank_name = (body.get("bank_name") or "").strip()
    bank_code = (body.get("bank_code") or "").strip()
    account_number = (body.get("account_number") or "").strip()
    account_name = (body.get("account_name") or "").strip()

    if not bank_name or not account_number or not account_name:
        raise HTTPException(status_code=400, detail="Bank name, account number, and account name are required")

    update_fields = {
        "bank_name": bank_name,
        "account_number": account_number,
        "account_name": account_name,
    }
    # bank_code is only sent by the combobox-driven registration form, not
    # the older plain-text bank-name prompt still used here — only touch
    # it when actually provided, so that flow doesn't silently wipe a
    # previously-verified code the payout system depends on.
    if bank_code:
        update_fields["bank_code"] = bank_code

    await db.affiliates.update_one(
        {"_id": affiliate["_id"]},
        {"$set": update_fields}
    )

    return {
        "status": "ok",
        "message": "Bank details updated successfully",
        "bank_name": bank_name,
        "account_number": account_number,
        "account_name": account_name,
    }
