"""
Lead Magnet Opt-In & Viral Referral Loop Routes.
Handles free cheat sheet opt-ins, welcome email dispatch, referral code generation,
and SparkLoop-style milestone tracking.
"""
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

from ..database import get_db

router = APIRouter(prefix="/api/lead-magnet", tags=["lead-magnet"])

# Fallback memory store for testing when db is None
_memory_subscribers = {}

class LeadOptInRequest(BaseModel):
    name: str
    email: EmailStr
    category: Optional[str] = "Sales & DM Closing"
    referral_code: Optional[str] = None

@router.post("/opt-in")
async def lead_magnet_opt_in(payload: LeadOptInRequest, db=Depends(get_db)):
    email_clean = payload.email.strip().lower()
    name_clean = payload.name.strip()

    if db is not None:
        existing = await db.lead_subscribers.find_one({"email": email_clean})
        
        if existing:
            ref_code = existing.get("ref_code")
            referral_count = existing.get("referrals_count", 0)
        else:
            ref_code = f"SCALE-{secrets.token_hex(3).upper()}"
            referred_by = None
            
            if payload.referral_code:
                referrer = await db.lead_subscribers.find_one({"ref_code": payload.referral_code.strip().upper()})
                if referrer:
                    referred_by = referrer["ref_code"]
                    await db.lead_subscribers.update_one(
                        {"_id": referrer["_id"]},
                        {"$inc": {"referrals_count": 1}}
                    )

            new_sub = {
                "name": name_clean,
                "email": email_clean,
                "category": payload.category,
                "ref_code": ref_code,
                "referred_by": referred_by,
                "referrals_count": 0,
                "created_at": datetime.now(timezone.utc),
                "last_active": datetime.now(timezone.utc),
                "status": "active"
            }
            await db.lead_subscribers.insert_one(new_sub)
            referral_count = 0

        # Queue automated Day 0 Welcome Email
        now_dt = datetime.now(timezone.utc)
        welcome_email_task = {
            "email": email_clean,
            "name": name_clean,
            "subject": "[FREE DOWNLOAD] The DM Sales Script: 5 Copy-Paste Messages That Turn 'How Much?' Into Bank Transfers",
            "template_name": "welcome_lead_magnet",
            "context": {
                "name": name_clean,
                "ref_code": ref_code,
                "referral_link": f"https://edgepack.thescaleconference.com/?ref={ref_code}"
            },
            "status": "pending",
            "created_at": now_dt
        }
        await db.email_queue.insert_one(welcome_email_task)

        # Queue 4-Day Automated Nurture & Conversion Sequence
        from datetime import timedelta
        sequence_schedule = [
            (1, "Why sending your price early is costing you ₦500k/month", "lead_sequence_01.html"),
            (2, "How Chidi closed a ₦750,000 retainer in 4 messages", "lead_sequence_02.html"),
            (3, "The complete DM closing playbook (Available now)", "lead_sequence_03.html"),
            (4, "Pick Any 3 Execution Playbooks for ₦12,000 (Save ₦3,000)", "lead_sequence_04.html"),
        ]

        for days_delay, subject, template in sequence_schedule:
            seq_task = {
                "email": email_clean,
                "name": name_clean,
                "subject": subject,
                "template": template,
                "status": "pending",
                "scheduled_at": now_dt + timedelta(days=days_delay),
                "created_at": now_dt,
                "kind": "lead_sequence"
            }
            await db.email_queue.insert_one(seq_task)
    else:
        # Fallback memory store when db is None
        if email_clean in _memory_subscribers:
            ref_code = _memory_subscribers[email_clean]["ref_code"]
            referral_count = _memory_subscribers[email_clean]["referrals_count"]
        else:
            ref_code = f"SCALE-{secrets.token_hex(3).upper()}"
            referred_by = None
            if payload.referral_code:
                for k, v in _memory_subscribers.items():
                    if v.get("ref_code") == payload.referral_code.strip().upper():
                        v["referrals_count"] = v.get("referrals_count", 0) + 1
                        referred_by = v["ref_code"]
                        break

            _memory_subscribers[email_clean] = {
                "name": name_clean,
                "email": email_clean,
                "category": payload.category,
                "ref_code": ref_code,
                "referred_by": referred_by,
                "referrals_count": 0,
            }
            referral_count = 0

    return {
        "status": "success",
        "message": "Free cheat sheet dispatched to inbox",
        "ref_code": ref_code,
        "referral_link": f"https://edgepack.thescaleconference.com/?ref={ref_code}",
        "referrals_count": referral_count
    }

@router.get("/referral-stats/{ref_code}")
async def get_referral_stats(ref_code: str, db=Depends(get_db)):
    code_clean = ref_code.strip().upper()
    
    if db is not None:
        sub = await db.lead_subscribers.find_one({"ref_code": code_clean})
    else:
        sub = next((v for v in _memory_subscribers.values() if v.get("ref_code") == code_clean), None)

    if not sub:
        raise HTTPException(status_code=404, detail="Referral profile not found")

    count = sub.get("referrals_count", 0)
    unlocked_bonus = count >= 2
    unlocked_free_book = count >= 5

    return {
        "ref_code": sub["ref_code"],
        "referrals_count": count,
        "unlocked_bonus": unlocked_bonus,
        "unlocked_free_book": unlocked_free_book,
        "next_milestone": 2 if count < 2 else (5 if count < 5 else 10)
    }
