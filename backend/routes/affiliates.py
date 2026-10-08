"""
Admin-side affiliate routes — create affiliates directly, list them with
click/conversion/commission stats, edit an individual affiliate's
commission percentage, and mark accumulated commission as paid.

This is a tracking system, not a payments system: "mark as paid" only
flips a status flag and timestamps it after the admin has already sent
money manually, outside this app. No Transfers API, no bank details, no
automated transfer is triggered anywhere here.

The public self-registration flow lives in routes/affiliate_public.py,
the affiliate's own read-only stats view in routes/affiliate_dashboard.py;
all three share the same creation logic via services/affiliate_service.py.

Referral attribution itself happens in payments.py (capturing the code
at checkout) and payment_completion.py (recording the conversion and
locking in the commission amount at that affiliate's rate at the time).
"""
import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..config import get_settings
from ..middleware.auth import require_admin
from ..database import get_db
from ..schemas.schemas import (
    AffiliateCreateRequest,
    AffiliateCommissionUpdateRequest,
    AffiliateStatusUpdateRequest,
    AffiliateDetailsUpdateRequest,
)
from ..services.affiliate_service import create_affiliate_record, ensure_affiliate_subaccount
from ..workers.email_scheduler import process_email_queue

router = APIRouter(prefix="/api/admin/affiliates", tags=["affiliates"])
settings = get_settings()


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
            commission_percent=body.commission_percent,
            bank_name=body.bank_name,
            bank_code=body.bank_code,
            account_number=body.account_number,
            account_name=body.account_name,
            invited_by=body.invited_by,
        )
    except ValueError as e:
        reason = str(e)
        if reason == "duplicate_email":
            raise HTTPException(status_code=409, detail="An affiliate with this email already exists")
        if reason == "duplicate_code":
            raise HTTPException(status_code=409, detail=f"Affiliate code '{body.code}' already exists")
        raise HTTPException(status_code=500, detail="Could not generate a unique affiliate code")

    affiliate = await ensure_affiliate_subaccount(db, affiliate)

    # Automatically generate activation token and send activation email
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=60)

    oid = ObjectId(affiliate["id"])
    await db.affiliates.update_one(
        {"_id": oid},
        {"$set": {
            "activation_token_hash": token_hash,
            "activation_token_expires_at": expires_at,
        }}
    )

    activation_link = f"{settings.APP_URL}/affiliate/activate?token={raw_token}"
    referral_link = f"{settings.APP_URL}/r/{affiliate['code']}"

    await db.email_queue.insert_one({
        "kind": "affiliate_activation",
        "email": affiliate["email"],
        "name": affiliate["name"],
        "code": affiliate["code"],
        "activation_link": activation_link,
        "scheduled_at": now,
        "status": "pending",
        "retry_count": 0,
        "sent_at": None,
        "error": None,
    })
    asyncio.create_task(process_email_queue())

    return {
        "id": affiliate["id"],
        "code": affiliate["code"],
        "name": affiliate["name"],
        "email": affiliate["email"],
        "active": True,
        "source": "admin_created",
        "commission_percent": affiliate["commission_percent"],
        "created_at": affiliate["created_at"],
        "clicks": 0,
        "conversions": 0,
        "revenue": 0,
        "commission_earned": 0,
        "commission_paid": 0,
        "commission_owed": 0,
        "bank_name": affiliate.get("bank_name", ""),
        "account_number": affiliate.get("account_number", ""),
        "account_name": affiliate.get("account_name", ""),
        "has_instant_split": bool(affiliate.get("subaccount_code")),
        "activation_link": activation_link,
        "referral_link": referral_link,
        "activation_status": "pending",
        "account_activated": False,
    }


@router.get("")
async def list_affiliates(
    page: int = 1, limit: int = 20,
    current_user=Depends(require_admin), db=Depends(get_db),
):
    skip = (page - 1) * limit
    affiliates = await db.affiliates.find({}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.affiliates.count_documents({})

    # Stats aggregations cover the whole collection (grouped by code, not
    # per-affiliate-doc) regardless of which page is being viewed — this is
    # a single query either way, not the O(n) pattern the 500-doc cap on
    # the affiliates list itself used to cause.
    click_counts = {
        row["_id"]: row["count"]
        for row in await db.referral_clicks.aggregate([
            {"$group": {"_id": "$affiliate_code", "count": {"$sum": 1}}}
        ]).to_list(10000)
    }
    referral_stats = {
        row["_id"]: row
        for row in await db.referrals.aggregate([
            {"$group": {
                "_id": "$affiliate_code",
                "conversions": {"$sum": 1},
                "revenue": {"$sum": "$amount"},
                "commission_earned": {"$sum": "$commission_amount"},
                "commission_paid": {
                    "$sum": {
                        "$cond": [{"$eq": ["$commission_status", "paid"]}, "$commission_amount", 0]
                    }
                },
            }}
        ]).to_list(10000)
    }

    recruit_counts = {
        row["_id"]: row["count"]
        for row in await db.affiliates.aggregate([
            {"$match": {"invited_by": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$invited_by", "count": {"$sum": 1}}}
        ]).to_list(10000)
    }

    out = []
    now = datetime.now(timezone.utc)
    for a in affiliates:
        code = a["code"]
        stats = referral_stats.get(code, {})
        earned = stats.get("commission_earned", 0) or 0
        paid = stats.get("commission_paid", 0) or 0

        is_activated = bool(a.get("account_activated") or a.get("password_hash"))
        if is_activated:
            act_status = "active"
        elif a.get("activation_token_hash"):
            exp = a.get("activation_token_expires_at")
            if exp and (exp.replace(tzinfo=timezone.utc) if exp.tzinfo is None else exp) > now:
                act_status = "pending"
            else:
                act_status = "not_activated"
        else:
            act_status = "not_activated"

        out.append({
            "id": str(a["_id"]),
            "code": code,
            "name": a["name"],
            "email": a["email"],
            "active": a.get("active", True),
            "source": a.get("source", "admin_created"),
            "invited_by": a.get("invited_by"),
            "recruited_count": recruit_counts.get(code, 0),
            "dashboard_token": a.get("dashboard_token"),
            "commission_percent": a.get("commission_percent", 0),
            "created_at": a["created_at"],
            "clicks": click_counts.get(code, 0),
            "conversions": stats.get("conversions", 0),
            "revenue": stats.get("revenue", 0) or 0,
            "commission_earned": earned,
            "commission_paid": paid,
            "commission_owed": earned - paid,
            "bank_name": a.get("bank_name", ""),
            "account_number": a.get("account_number", ""),
            "account_name": a.get("account_name", ""),
            "has_instant_split": bool(a.get("subaccount_code")),
            "activation_status": act_status,
            "account_activated": is_activated,
            "last_login": a.get("last_login"),
        })
    return {"affiliates": out, "total": total, "page": page, "pages": -(-total // limit)}


@router.patch("/{affiliate_id}/commission")
async def update_commission(
    affiliate_id: str,
    body: AffiliateCommissionUpdateRequest,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    """
    Changes the rate applied to future conversions only. Every conversion
    already recorded has its commission_amount locked in at the rate that
    applied at the time (see payment_completion.py) — this update never
    retroactively touches past sales.
    """
    try:
        oid = ObjectId(affiliate_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid affiliate id")

    result = await db.affiliates.update_one(
        {"_id": oid}, {"$set": {"commission_percent": body.commission_percent}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Affiliate not found")

    # Keep an existing Paystack subaccount's split percentage in sync —
    # otherwise a rate change here would silently stop applying to
    # affiliates who get paid via instant split.
    affiliate = await db.affiliates.find_one({"_id": oid})
    if affiliate and affiliate.get("subaccount_code"):
        await ensure_affiliate_subaccount(db, affiliate)

    return {"success": True, "commission_percent": body.commission_percent}


@router.post("/{affiliate_id}/mark-paid")
async def mark_commission_paid(
    affiliate_id: str,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    """
    Manual settlement log — call this only after you've actually sent the
    affiliate money yourself (bank transfer, outside this app). Flips
    every currently-unpaid conversion for this affiliate to "paid" and
    timestamps it; triggers no real transfer of any kind.
    """
    try:
        oid = ObjectId(affiliate_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid affiliate id")

    affiliate = await db.affiliates.find_one({"_id": oid})
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")

    code = affiliate["code"]
    unpaid = await db.referrals.find(
        {"affiliate_code": code, "commission_status": "unpaid"}
    ).to_list(10000)

    if not unpaid:
        return {"success": True, "amount_marked_paid": 0, "message": "No outstanding commission to mark as paid."}

    total = sum(r.get("commission_amount", 0) or 0 for r in unpaid)
    now = datetime.now(timezone.utc)
    payout_ref = f"MANUAL-{now.strftime('%Y%m%d%H%M%S')}"
    await db.referrals.update_many(
        {"affiliate_code": code, "commission_status": "unpaid"},
        {"$set": {"commission_status": "paid", "paid_at": now, "payout_reference": payout_ref}},
    )
    return {"success": True, "amount_marked_paid": total, "paid_at": now, "payout_reference": payout_ref}


@router.post("/{affiliate_id}/resend-activation")
async def resend_affiliate_activation(
    affiliate_id: str,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    """
    Manually triggers or resends an account activation email to an affiliate.
    Generates a secure 60-minute single-use token and queues an activation email.
    """
    try:
        oid = ObjectId(affiliate_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid affiliate id")

    affiliate = await db.affiliates.find_one({"_id": oid})
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")

    email = affiliate.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Affiliate has no email address configured")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=60)

    await db.affiliates.update_one(
        {"_id": oid},
        {"$set": {
            "activation_token_hash": token_hash,
            "activation_token_expires_at": expires_at,
        }}
    )

    activation_link = f"{settings.APP_URL}/affiliate/activate?token={raw_token}"

    await db.email_queue.insert_one({
        "kind": "affiliate_activation",
        "email": affiliate["email"],
        "name": affiliate["name"],
        "code": affiliate["code"],
        "activation_link": activation_link,
        "scheduled_at": now,
        "status": "pending",
        "retry_count": 0,
        "sent_at": None,
        "error": None,
    })
    asyncio.create_task(process_email_queue())

    return {
        "success": True,
        "message": f"Activation email sent to {affiliate['email']}",
        "activation_link": activation_link,
    }


@router.patch("/{affiliate_id}/status")
async def update_affiliate_status(
    affiliate_id: str,
    body: AffiliateStatusUpdateRequest,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    """
    Toggle affiliate active/suspended status.
    Suspended affiliates cannot log in, track clicks, or receive referrals.
    """
    try:
        oid = ObjectId(affiliate_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid affiliate id")

    result = await db.affiliates.update_one(
        {"_id": oid},
        {"$set": {"active": body.active}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Affiliate not found")

    return {
        "success": True,
        "active": body.active,
        "message": "Affiliate activated successfully" if body.active else "Affiliate suspended successfully"
    }


@router.patch("/{affiliate_id}/details")
async def update_affiliate_details(
    affiliate_id: str,
    body: AffiliateDetailsUpdateRequest,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    """
    Update partner profile details: name, email, bank details, or commission percentage.
    Automatically re-synchronizes Paystack subaccount if bank info or commission changes.
    """
    try:
        oid = ObjectId(affiliate_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid affiliate id")

    affiliate = await db.affiliates.find_one({"_id": oid})
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")

    update_fields = {}
    if body.name is not None and body.name.strip():
        update_fields["name"] = body.name.strip()

    if body.email is not None:
        new_email = str(body.email).strip().lower()
        if new_email != affiliate["email"].lower():
            existing = await db.affiliates.find_one({"email": new_email, "_id": {"$ne": oid}})
            if existing:
                raise HTTPException(status_code=409, detail="An affiliate with this email already exists")
            update_fields["email"] = new_email

    if body.bank_name is not None:
        update_fields["bank_name"] = body.bank_name.strip()
    if body.bank_code is not None:
        update_fields["bank_code"] = body.bank_code.strip()
    if body.account_number is not None:
        clean_num = body.account_number.strip()
        if clean_num and not clean_num.isdigit():
            raise HTTPException(status_code=400, detail="Account number must contain digits only")
        update_fields["account_number"] = clean_num
    if body.account_name is not None:
        update_fields["account_name"] = body.account_name.strip()
    if body.commission_percent is not None:
        update_fields["commission_percent"] = body.commission_percent

    if not update_fields:
        return {"success": True, "message": "No changes provided"}

    await db.affiliates.update_one({"_id": oid}, {"$set": update_fields})
    updated = await db.affiliates.find_one({"_id": oid})

    # If bank details or commission changed, re-sync Paystack subaccount
    if any(k in update_fields for k in ["bank_name", "bank_code", "account_number", "account_name", "commission_percent"]):
        updated = await ensure_affiliate_subaccount(db, updated)

    return {
        "success": True,
        "message": "Affiliate details updated successfully",
        "affiliate": {
            "id": str(updated["_id"]),
            "code": updated["code"],
            "name": updated["name"],
            "email": updated["email"],
            "commission_percent": updated.get("commission_percent", 50.0),
            "bank_name": updated.get("bank_name", ""),
            "bank_code": updated.get("bank_code", ""),
            "account_number": updated.get("account_number", ""),
            "account_name": updated.get("account_name", ""),
            "has_instant_split": bool(updated.get("subaccount_code")),
        }
    }

