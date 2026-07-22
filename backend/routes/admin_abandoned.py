"""
Admin endpoints for Abandoned Transaction Recovery System.
All routes require admin JWT authentication.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..middleware.auth import require_admin
from ..database import get_db
from ..config import get_settings
from ..workers.abandoned_recovery_scheduler import run_abandoned_recovery_check

router = APIRouter(prefix="/api/admin/abandoned-transactions", tags=["admin_abandoned"])
settings = get_settings()


@router.get("")
async def get_abandoned_transactions(
    status: Optional[str] = Query(None, description="Filter by status: pending, sequence_active, recovered, completed, unsubscribed"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    """
    Returns summary statistics and paginated list of abandoned transactions.
    """
    match_q = {}
    if status:
        match_q["status"] = status
    if search:
        s = search.strip()
        match_q["$or"] = [
            {"email": {"$regex": s, "$options": "i"}},
            {"name": {"$regex": s, "$options": "i"}},
            {"reference": {"$regex": s, "$options": "i"}},
        ]

    total_records = await db.abandoned_transactions.count_documents(match_q)
    skip = (page - 1) * limit

    cursor = db.abandoned_transactions.find(match_q).sort("created_at", -1).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)

    # ── Summary metrics ────────────────────────────────────────────────
    total_abandoned = await db.abandoned_transactions.count_documents({"status": {"$ne": "superseded"}})
    total_recovered = await db.abandoned_transactions.count_documents({"status": "recovered"})
    total_active_sequences = await db.abandoned_transactions.count_documents({"status": "sequence_active"})

    # Count total individual emails sent
    pipeline = [
        {"$unwind": "$emails_sent"},
        {"$match": {"emails_sent.success": True}},
        {"$count": "total_emails"}
    ]
    res = await db.abandoned_transactions.aggregate(pipeline).to_list(1)
    total_emails_sent = res[0]["total_emails"] if res else 0

    recovery_rate = round((total_recovered / total_abandoned * 100), 2) if total_abandoned > 0 else 0.0

    return {
        "summary": {
            "system_enabled": settings.ABANDONED_RECOVERY_ENABLED,
            "total_abandoned": total_abandoned,
            "total_recovered": total_recovered,
            "total_active_sequences": total_active_sequences,
            "total_emails_sent": total_emails_sent,
            "recovery_rate_percent": recovery_rate,
            "config": {
                "delay_minutes_1": settings.ABANDONED_DELAY_MINUTES_1,
                "delay_minutes_2": settings.ABANDONED_DELAY_MINUTES_2,
                "delay_minutes_3": settings.ABANDONED_DELAY_MINUTES_3,
                "discount_enabled": settings.ABANDONED_DISCOUNT_ENABLED,
                "discount_percent": settings.ABANDONED_DISCOUNT_PERCENT,
                "discount_code": settings.ABANDONED_DISCOUNT_CODE,
            }
        },
        "pagination": {
            "total": total_records,
            "page": page,
            "limit": limit,
            "pages": (total_records + limit - 1) // limit if limit > 0 else 1,
        },
        "items": items,
    }


@router.post("/toggle")
async def toggle_recovery_system(
    enabled: Optional[bool] = None,
    current_user=Depends(require_admin),
):
    """
    Toggle the abandoned recovery system on or off.
    """
    if enabled is not None:
        settings.ABANDONED_RECOVERY_ENABLED = enabled
    else:
        settings.ABANDONED_RECOVERY_ENABLED = not settings.ABANDONED_RECOVERY_ENABLED

    state_str = "active" if settings.ABANDONED_RECOVERY_ENABLED else "paused"
    print(f"⚙️ Abandoned recovery system is now {state_str}")
    return {
        "success": True,
        "system_enabled": settings.ABANDONED_RECOVERY_ENABLED,
        "message": f"Abandoned recovery system is now {state_str}.",
    }


@router.post("/trigger-check")
async def trigger_manual_recovery_check(
    current_user=Depends(require_admin),
):
    """
    Manually trigger an immediate check and processing run for abandoned transactions.
    """
    asyncio.create_task(run_abandoned_recovery_check())
    return {
        "success": True,
        "message": "Manual abandoned transaction recovery check triggered in background.",
    }
