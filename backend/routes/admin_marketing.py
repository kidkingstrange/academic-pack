"""
Admin Marketing & Revenue Generation Engine API Routes.
Provides endpoints for audience segmentation, product knowledge base,
AI direct-response copy generation, campaign management, testing, and queue dispatch.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, EmailStr

from ..database import get_db
from ..middleware.auth import require_admin
from ..services.marketing_service import (
    get_marketing_overview,
    get_product_knowledge_base,
    get_audience_segments,
    generate_ai_campaign_copy,
    create_campaign,
    send_test_campaign_email,
    launch_campaign,
)

router = APIRouter(prefix="/api/admin/marketing", tags=["admin-marketing"])


# ── Request / Response Schemas ──────────────────────────────────────────────

class GenerateCopyRequest(BaseModel):
    product_slug: str
    campaign_type: Optional[str] = "direct_response"
    target_segment: Optional[str] = "all_consented"


class CreateCampaignRequest(BaseModel):
    title: str
    product_slug: str
    target_segment: str = "all_consented"
    subject: str
    preview_text: str
    html_body: str
    plain_text: Optional[str] = None
    scheduled_at: Optional[str] = None


class TestSendRequest(BaseModel):
    test_email: EmailStr


class QuickTestRequest(BaseModel):
    recipient: EmailStr = "daviditoyaa@gmail.com"
    product_slug: Optional[str] = "quitting-the-handjob"
    campaign_type: Optional[str] = "direct_response"


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/overview")
async def get_overview(current_user=Depends(require_admin), db=Depends(get_db)):
    """Return marketing KPIs, audience size, campaign counts, and revenue attribution."""
    return await get_marketing_overview(db)


@router.get("/products")
async def list_products(current_user=Depends(require_admin)):
    """Return the structured internal Product Knowledge Base."""
    return get_product_knowledge_base()


@router.get("/segments")
async def list_segments(current_user=Depends(require_admin), db=Depends(get_db)):
    """Return available customer segments with live count of eligible consented recipients."""
    return await get_audience_segments(db)


@router.post("/generate-copy")
async def generate_copy(payload: GenerateCopyRequest, current_user=Depends(require_admin)):
    """
    AI-powered direct-response email copy generator.
    Produces high-converting subject line options, preview text, and responsive HTML body
    grounded strictly in verified product benefits and pricing.
    """
    try:
        copy_data = generate_ai_campaign_copy(
            product_slug=payload.product_slug,
            campaign_type=payload.campaign_type or "direct_response",
            target_segment=payload.target_segment or "all_consented",
        )
        return copy_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate campaign copy: {e}")


@router.get("/campaigns")
async def list_campaigns(current_user=Depends(require_admin), db=Depends(get_db)):
    """List all marketing campaigns sorted by creation date."""
    if db is None:
        return []
    cursor = db.marketing_campaigns.find({}, {"_id": 0}).sort("created_at", -1)
    campaigns = await cursor.to_list(100)
    for c in campaigns:
        for k in ("created_at", "scheduled_at", "sent_at", "launched_at", "updated_at"):
            if c.get(k) and isinstance(c[k], datetime):
                c[k] = c[k].isoformat()
    return campaigns


@router.post("/campaigns")
async def save_campaign(payload: CreateCampaignRequest, current_user=Depends(require_admin), db=Depends(get_db)):
    """Save a new campaign draft or scheduled broadcast."""
    scheduled_dt = None
    if payload.scheduled_at:
        try:
            scheduled_dt = datetime.fromisoformat(payload.scheduled_at.replace("Z", "+00:00"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid scheduled_at ISO timestamp format.")

    doc = await create_campaign(
        db,
        title=payload.title,
        product_slug=payload.product_slug,
        target_segment=payload.target_segment,
        subject=payload.subject,
        preview_text=payload.preview_text,
        html_body=payload.html_body,
        plain_text=payload.plain_text,
        scheduled_at=scheduled_dt,
    )
    doc_copy = dict(doc)
    doc_copy.pop("_id", None)
    for k in ("created_at", "scheduled_at", "sent_at", "launched_at", "updated_at"):
        if doc_copy.get(k) and isinstance(doc_copy[k], datetime):
            doc_copy[k] = doc_copy[k].isoformat()
    return doc_copy


@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str, current_user=Depends(require_admin), db=Depends(get_db)):
    """Retrieve full details and delivery stats for a specific campaign."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    camp = await db.marketing_campaigns.find_one({"campaign_id": campaign_id}, {"_id": 0})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    for k in ("created_at", "scheduled_at", "sent_at", "launched_at", "updated_at"):
        if camp.get(k) and isinstance(camp[k], datetime):
            camp[k] = camp[k].isoformat()
    return camp


@router.get("/smtp-diagnostics")
async def smtp_diagnostics():
    """Diagnostic check to inspect active live SMTP host and sender without exposing credentials."""
    from ..config import get_settings
    s = get_settings()
    return {
        "smtp_host": s.SMTP_HOST,
        "smtp_port": s.SMTP_PORT,
        "smtp_user": s.SMTP_USER,
        "from_email": s.FROM_EMAIL,
        "has_password": bool(s.SMTP_PASS and s.SMTP_PASS not in ("your-app-password", "your-smtp-password", "")),
    }


@router.post("/dispatch-preview-test")
async def dispatch_preview_test(payload: QuickTestRequest, db=Depends(get_db)):
    """Direct test dispatch to authorized admin email (strictly locked to daviditoyaa@gmail.com).
    Uses production SMTP settings to deliver a real sample email.
    """
    clean_target = payload.recipient.strip().lower()
    if clean_target != "daviditoyaa@gmail.com":
        raise HTTPException(
            status_code=403,
            detail="Quick preview test is strictly locked to verified admin email daviditoyaa@gmail.com."
        )

    # Generate copy
    copy_data = generate_ai_campaign_copy(
        product_slug=payload.product_slug or "quitting-the-handjob",
        campaign_type=payload.campaign_type or "direct_response",
        target_segment="all_consented",
    )

    # Save draft campaign in db
    camp = await create_campaign(
        db,
        title=f"Live Test Preview - {payload.product_slug}",
        product_slug=payload.product_slug or "quitting-the-handjob",
        target_segment="all_consented",
        subject=copy_data["recommended_subject"],
        preview_text=copy_data["preview_text"],
        html_body=copy_data["html_body"],
        plain_text=copy_data["plain_text"],
    )

    # Send test
    success, err = await send_test_campaign_email(db, camp["campaign_id"], clean_target)
    if not success:
        raise HTTPException(status_code=500, detail=f"Live SMTP dispatch failed: {err}")

    return {
        "success": True,
        "message": f"Real test email successfully dispatched to {clean_target} via live production SMTP!",
        "subject": copy_data["recommended_subject"],
        "campaign_id": camp["campaign_id"],
    }


@router.post("/campaigns/{campaign_id}/test")
async def test_campaign(campaign_id: str, payload: TestSendRequest, current_user=Depends(require_admin), db=Depends(get_db)):
    """Send an immediate test preview email to verified test recipient."""
    success, err = await send_test_campaign_email(db, campaign_id, payload.test_email)
    if not success:
        raise HTTPException(status_code=400, detail=f"Test send failed: {err}")
    return {"success": True, "message": f"Test preview dispatched successfully to {payload.test_email}."}


@router.post("/campaigns/{campaign_id}/launch")
async def dispatch_campaign(campaign_id: str, current_user=Depends(require_admin), db=Depends(get_db)):
    """Launch campaign broadcast to all consented recipients in target segment."""
    res = await launch_campaign(db, campaign_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Launch failed."))
    return res


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str, current_user=Depends(require_admin), db=Depends(get_db)):
    """Delete an unlaunched campaign draft."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    camp = await db.marketing_campaigns.find_one({"campaign_id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if camp.get("status") in ("sending", "sent"):
        raise HTTPException(status_code=400, detail="Cannot delete a campaign that has already been launched.")
    await db.marketing_campaigns.delete_one({"campaign_id": campaign_id})
    return {"success": True, "message": "Campaign draft deleted."}


@router.get("/settings")
async def get_settings_endpoint(current_user=Depends(require_admin), db=Depends(get_db)):
    """Return runtime automation settings and workflow statuses."""
    from ..workers.lifecycle_marketing_scheduler import get_marketing_settings
    return await get_marketing_settings(db)


@router.post("/settings")
async def update_settings_endpoint(payload: dict, current_user=Depends(require_admin), db=Depends(get_db)):
    """Update runtime automation toggles."""
    from ..workers.lifecycle_marketing_scheduler import update_marketing_settings
    return await update_marketing_settings(db, payload)


@router.post("/trigger-scan")
async def trigger_lifecycle_scan(current_user=Depends(require_admin), db=Depends(get_db)):
    """Trigger an immediate scan for post-purchase cross-sell & win-back opportunities."""
    from ..workers.lifecycle_marketing_scheduler import run_lifecycle_cross_sell_scan
    result = await run_lifecycle_cross_sell_scan()
    return {"success": True, **result}

