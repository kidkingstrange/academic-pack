"""
Public, unauthenticated affiliate self-registration. Anyone can reach
this — no admin review gate — so keep validation lightweight but real
(a rate limit, a duplicate-email check). Active immediately, same as
before: there's no payout information to collect here at all, since this
system never moves money — the admin pays affiliates manually and marks
it settled from the admin dashboard.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from ..database import get_db
from ..config import get_settings
from ..schemas.schemas import AffiliateRegisterRequest
from ..services.affiliate_service import create_affiliate_record
from ..workers.email_scheduler import process_email_queue

router = APIRouter(prefix="/api/affiliates", tags=["affiliates-public"])
settings = get_settings()

REGISTRATIONS_PER_IP_PER_HOUR = 5


@router.post("/register")
async def register_affiliate(body: AffiliateRegisterRequest, request: Request, db=Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    now = datetime.now(timezone.utc)

    # ── Lightweight rate limit ──────────────────────────────────────────
    # Not full fraud detection — just a cap on scripted mass signups from
    # one network. Counts successful registrations, not raw attempts.
    one_hour_ago = now - timedelta(hours=1)
    recent = await db.affiliates.count_documents({
        "registration_ip": ip,
        "created_at": {"$gte": one_hour_ago},
    })
    if recent >= REGISTRATIONS_PER_IP_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many registrations from this network. Please try again later.")

    try:
        affiliate = await create_affiliate_record(
            db, name=body.name, email=body.email, source="self_registered",
            registration_ip=ip, bank_name=body.bank_name, account_number=body.account_number,
            account_name=body.account_name,
        )
    except ValueError as e:
        if str(e) == "duplicate_email":
            raise HTTPException(status_code=409, detail="An affiliate account with this email already exists.")
        raise HTTPException(status_code=500, detail="Could not complete registration. Please try again.")

    referral_link = f"{settings.APP_URL}/r/{affiliate['code']}"
    dashboard_link = f"{settings.APP_URL}/affiliate/dashboard?token={affiliate['dashboard_token']}"

    # Queue the confirmation email — same retry-safe pattern as every
    # other transactional email in this app (see complete_payment()):
    # insert into email_queue, then fire an immediate attempt, so a
    # transient SMTP failure gets retried by the 5-minute scheduler
    # instead of the affiliate silently never receiving it.
    await db.email_queue.insert_one({
        "kind": "affiliate_welcome",
        "email": affiliate["email"],
        "name": affiliate["name"],
        "code": affiliate["code"],
        "referral_link": referral_link,
        "dashboard_link": dashboard_link,
        "scheduled_at": now,
        "status": "pending",
        "retry_count": 0,
        "sent_at": None,
        "error": None,
    })
    asyncio.create_task(process_email_queue())

    return {
        "code": affiliate["code"],
        "referral_link": referral_link,
        "dashboard_link": dashboard_link,
        "name": affiliate["name"],
        "email": affiliate["email"],
    }


@router.get("/resolve-bank")
async def resolve_bank_account(account_number: str, bank_code: str):
    """
    Public live validation endpoint for affiliate registration & bank updates.
    Queries Paystack NIBSS API to resolve 10-digit NUBAN account number & holder name.
    """
    clean_acc = "".join(filter(str.isdigit, account_number))
    if len(clean_acc) != 10:
        raise HTTPException(status_code=400, detail="Account number must be exactly 10 digits")
    if not bank_code:
        raise HTTPException(status_code=400, detail="Please select a bank first")

    from ..services.paystack import resolve_account_number
    res = await resolve_account_number(clean_acc, bank_code)
    
    if not res.get("status"):
        msg = res.get("message") or "Could not verify account number at selected bank"
        raise HTTPException(status_code=422, detail=msg)
        
    data = res.get("data", {})
    return {
        "status": True,
        "account_number": data.get("account_number", clean_acc),
        "account_name": data.get("account_name", ""),
    }
