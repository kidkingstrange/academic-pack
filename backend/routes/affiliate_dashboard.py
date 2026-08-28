"""
Affiliate-facing read-only stats — no password, just their private
dashboard_token (distinct from their public referral `code`, which is
shared everywhere in links and can never double as a login credential).

Returns only what an affiliate needs to see about themselves: their own
clicks, conversions, revenue, commission rate, and what's been paid vs
still owed. No other affiliate's data is ever reachable through this.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..config import get_settings
from ..database import get_db
from ..schemas.schemas import AffiliateBankDetailsUpdateRequest
from ..services.affiliate_service import ensure_affiliate_subaccount
from ..services.marketing_assets import get_asset, list_assets_for_affiliate

router = APIRouter(prefix="/api/affiliate", tags=["affiliate-dashboard"])
settings = get_settings()


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

    from ..services.affiliate_milestone_service import (
        get_affiliate_recruits_and_bonuses, MILESTONE_SALES_TARGET,
        DIRECT_10_SALES_BONUS, PARENT_RECRUITER_BONUS,
    )
    recruits_data = await get_affiliate_recruits_and_bonuses(db, code)

    direct_progress = min(100, round((len(referrals) / MILESTONE_SALES_TARGET) * 100, 1))
    direct_unlocked = any(m.get("type") == "direct_10_sales" for m in recruits_data["milestones"]) or len(referrals) >= MILESTONE_SALES_TARGET

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
        "referral_link": f"{settings.APP_URL}/r/{code}",
        "affiliate_invite_link": f"{settings.APP_URL}/affiliate/register?invite={code}",
        "milestone_target": MILESTONE_SALES_TARGET,
        "direct_milestone_bonus": DIRECT_10_SALES_BONUS,
        "parent_recruiter_bonus": PARENT_RECRUITER_BONUS,
        "direct_milestone_progress": direct_progress,
        "direct_milestone_unlocked": direct_unlocked,
        "invited_affiliates": recruits_data["invited_affiliates"],
        "milestones": recruits_data["milestones"],
        "total_bonus_unlocked": recruits_data["total_bonus_unlocked"],
        "total_bonus_paid": recruits_data["total_bonus_paid"],
        "total_recruits": recruits_data["total_recruits"],
        "video_materials_link": settings.AFFILIATE_VIDEO_MATERIALS_LINK,
        "whatsapp_affiliate_link": settings.WHATSAPP_AFFILIATE_LINK,
    }


@router.post("/bank-details")
async def update_my_bank_details(token: str, body: AffiliateBankDetailsUpdateRequest, db=Depends(get_db)):
    affiliate = await db.affiliates.find_one({"dashboard_token": token})
    if not affiliate:
        raise HTTPException(status_code=401, detail="Invalid dashboard link")

    bank_name = body.bank_name.strip()
    bank_code = (body.bank_code or "").strip()
    account_number = body.account_number.strip()
    account_name = body.account_name.strip()

    if not account_number.isdigit():
        raise HTTPException(status_code=400, detail="Account number must contain digits only")

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
    affiliate.update(update_fields)
    await ensure_affiliate_subaccount(db, affiliate)

    # Auto-disburse any unlocked milestone bonuses that were waiting for bank details
    from ..services.affiliate_milestone_service import auto_disburse_pending_milestones_for_affiliate
    payout_results = await auto_disburse_pending_milestones_for_affiliate(db, affiliate["code"])

    return {
        "status": "ok",
        "message": "Bank details updated successfully",
        "bank_name": bank_name,
        "account_number": account_number,
        "account_name": account_name,
        "payout_results": payout_results,
    }


@router.get("/marketing-assets")
async def get_marketing_assets(token: str, db=Depends(get_db)):
    affiliate = await db.affiliates.find_one({"dashboard_token": token})
    if not affiliate:
        raise HTTPException(status_code=401, detail="Invalid dashboard link")

    referral_link = f"{settings.APP_URL}/r/{affiliate['code']}"
    return {"assets": list_assets_for_affiliate(referral_link)}


@router.post("/marketing-assets/log-download")
async def log_marketing_asset_download(token: str, body: dict, db=Depends(get_db)):
    """
    Records a download event — counts toward "activated" status (see
    services/affiliate_health_service.py) and starts the 3-day nudge
    clock (workers/affiliate_nudge_scheduler.py) if they never click
    their own link afterward.
    """
    affiliate = await db.affiliates.find_one({"dashboard_token": token})
    if not affiliate:
        raise HTTPException(status_code=401, detail="Invalid dashboard link")

    asset_name = (body.get("asset_name") or "").strip()
    if not get_asset(asset_name):
        raise HTTPException(status_code=400, detail="Unknown asset")

    await db.marketing_asset_downloads.insert_one({
        "affiliate_code": affiliate["code"],
        "asset_name": asset_name,
        "downloaded_at": datetime.now(timezone.utc),
        "nudge_sent": False,
    })
    return {"status": "ok"}


@router.post("/video-click")
async def log_marketing_video_click(token: str, db=Depends(get_db)):
    """
    Records a video click event — counts toward "activated" status (see
    services/affiliate_health_service.py) and starts the 3-day nudge
    clock (workers/affiliate_nudge_scheduler.py) if they never click
    their own link afterward.
    """
    affiliate = await db.affiliates.find_one({"dashboard_token": token})
    if not affiliate:
        raise HTTPException(status_code=401, detail="Invalid dashboard link")

    await db.marketing_video_clicks.insert_one({
        "affiliate_id": affiliate["_id"],
        "affiliate_code": affiliate["code"],
        "clicked_at": datetime.now(timezone.utc),
        "nudge_sent": False,
    })
    return {"status": "ok"}
