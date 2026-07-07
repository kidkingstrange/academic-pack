"""
Community routes — WhatsApp community join with email capture.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, EmailStr
from ..database import get_db
from ..workers.email_scheduler import enqueue_sequence_for_subscriber

router = APIRouter(prefix="/api/community", tags=["community"])


class CommunityJoinRequest(BaseModel):
    email: EmailStr


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

    # Check if already a subscriber
    existing_sub = await db.subscribers.find_one({"email": email})

    if existing_sub:
        # Already in system — just add community tag if not present
        if "community" not in existing_sub.get("tags", []):
            await db.subscribers.update_one(
                {"_id": existing_sub["_id"]},
                {"$addToSet": {"tags": "community"}},
            )
        return {"success": True, "message": "Welcome back! Redirecting to community."}

    import secrets
    unsub_token = secrets.token_urlsafe(32)

    # Create new subscriber with community tag
    sub_result = await db.subscribers.insert_one({
        "name": email.split("@")[0].title(),  # Use email prefix as name
        "email": email,
        "subscribed_at": now,
        "sequence_position": 0,
        "next_send_at": now,
        "is_active": True,
        "tags": ["community"],
        "source": "whatsapp_community",
        "ip_address": request.client.host,
        "unsubscribe_token": unsub_token,
    })

    # Also save as lead
    await db.leads.update_one(
        {"email": email},
        {"$set": {
            "name": email.split("@")[0].title(),
            "email": email,
            "source": "whatsapp_community",
            "ip_address": request.client.host,
            "created_at": now,
            "converted": False,
        }},
        upsert=True,
    )

    # Queue the full 52-email sequence
    import asyncio
    asyncio.create_task(enqueue_sequence_for_subscriber(sub_result.inserted_id, now))

    return {"success": True, "message": "You're in! Redirecting to community."}
