"""
Public, unauthenticated affiliate routes: self-registration and the bank
list that populates its dropdown. Anyone can reach these — no admin
review gate — so keep validation here lightweight but real (rate limit,
duplicate-email check); actual payout runs are a separate, admin-gated
step (see routes/affiliates.py's deactivate endpoint and the Part 2 plan).
"""
import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from ..database import get_db
from ..config import get_settings
from ..schemas.schemas import AffiliateRegisterRequest
from ..services.affiliate_service import create_affiliate_record
from ..services.flutterwave import get_flw_token, list_banks
from ..workers.email_scheduler import process_email_queue

router = APIRouter(prefix="/api/affiliates", tags=["affiliates-public"])
settings = get_settings()

REGISTRATIONS_PER_IP_PER_HOUR = 5


@router.get("/banks")
async def get_banks():
    try:
        token = await get_flw_token()
        banks = await list_banks(token)
    except Exception as e:
        print(f"❌ FLW banks lookup error: {e}")
        raise HTTPException(status_code=502, detail="Could not load bank list. Please try again.")
    return {"banks": banks}


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
            db,
            name=body.name,
            email=body.email,
            source="self_registered",
            bank_details={
                "account_number": body.bank_account_number,
                "bank_code": body.bank_code,
                "bank_name": body.bank_name,
            },
            promotion_info=body.promotion_info,
            registration_ip=ip,
        )
    except ValueError as e:
        if str(e) == "duplicate_email":
            raise HTTPException(status_code=409, detail="An affiliate account with this email already exists.")
        raise HTTPException(status_code=500, detail="Could not complete registration. Please try again.")

    referral_link = f"{settings.APP_URL}/r/{affiliate['code']}"

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
        "name": affiliate["name"],
        "email": affiliate["email"],
    }
