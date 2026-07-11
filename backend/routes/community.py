"""
Community routes — WhatsApp community join with email capture.
"""
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, EmailStr
from ..database import get_db
from ..workers.email_scheduler import enqueue_sequence_for_subscriber

router = APIRouter(prefix="/api/community", tags=["community"])


class CommunityJoinRequest(BaseModel):
    email: EmailStr
    referral_code: Optional[str] = None


@router.post("/join")
async def join_community(body: CommunityJoinRequest, request: Request, db=Depends(get_db)):
    """
    Collect email for WhatsApp community access.
    Adds subscriber to the 52-email sequence if not already subscribed.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    email = body.email.lower()
    now = datetime.now(timezone.utc)

    # ── Resolve referral code with self-referral check ──
    referred_by = None
    if body.referral_code:
        candidate = body.referral_code.strip().upper()
        if candidate:
            affiliate = await db.affiliates.find_one({"code": candidate, "active": True})
            if affiliate:
                # Prevent self-referral: email check and IP check
                client_ip = request.client.host if request.client else None
                if affiliate["email"] != email and (not client_ip or affiliate.get("registration_ip") != client_ip):
                    referred_by = candidate

    # Check if already a subscriber
    existing_sub = await db.subscribers.find_one({"email": email})

    if existing_sub:
        # Already in system — just add community tag if not present
        update_doc = {"$addToSet": {"tags": "community"}}
        if referred_by and not existing_sub.get("referred_by"):
            update_doc["$set"] = {"referred_by": referred_by}
            
        await db.subscribers.update_one({"_id": existing_sub["_id"]}, update_doc)
        
        # Keep lead referred_by updated too
        if referred_by:
            await db.leads.update_one(
                {"email": email},
                {"$set": {"referred_by": referred_by}}
            )
        return {"success": True, "message": "Welcome back! Redirecting to community."}

    import secrets
    unsub_token = secrets.token_urlsafe(32)

    # Create new subscriber with community tag
    sub_doc = {
        "name": email.split("@")[0].title(),  # Use email prefix as name
        "email": email,
        "subscribed_at": now,
        "sequence_position": 0,
        "next_send_at": now,
        "is_active": True,
        "tags": ["community"],
        "source": "whatsapp_community",
        "ip_address": request.client.host if request.client else None,
        "unsubscribe_token": unsub_token,
    }
    if referred_by:
        sub_doc["referred_by"] = referred_by

    sub_result = await db.subscribers.insert_one(sub_doc)

    # Also save as lead
    lead_set = {
        "name": email.split("@")[0].title(),
        "email": email,
        "source": "whatsapp_community",
        "ip_address": request.client.host if request.client else None,
        "created_at": now,
        "converted": False,
    }
    if referred_by:
        lead_set["referred_by"] = referred_by

    await db.leads.update_one(
        {"email": email},
        {"$set": lead_set},
        upsert=True,
    )

    # Queue the full 52-email sequence
    import asyncio
    asyncio.create_task(enqueue_sequence_for_subscriber(sub_result.inserted_id, now))

    return {"success": True, "message": "You're in! Redirecting to community."}
