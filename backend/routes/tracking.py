"""
Client telemetry tracking endpoints for funnel, source, and device analytics.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..utils.rate_limit import get_real_client_ip

router = APIRouter(prefix="/api/tracking", tags=["tracking"])

class TelemetryEventRequest(BaseModel):
    event_name: str  # e.g., landing_view, checkout_view, checkout_start, abandoned_checkout, exit_page
    referral_code: Optional[str] = None
    utm_source: Optional[str] = None
    url: Optional[str] = None
    device_type: Optional[str] = None  # desktop, mobile, tablet
    browser: Optional[str] = None
    os: Optional[str] = None

@router.post("/event")
async def track_event(body: TelemetryEventRequest, request: Request, db=Depends(get_db)):
    """Log client telemetry event for funnel and traffic source analytics."""
    ip_address = get_real_client_ip(request)
    user_agent = request.headers.get("user-agent", "")

    # Basic UA parsing if not provided
    ua_lower = user_agent.lower()
    device = body.device_type
    if not device:
        if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            device = "mobile"
        elif "ipad" in ua_lower or "tablet" in ua_lower:
            device = "tablet"
        else:
            device = "desktop"

    browser = body.browser
    if not browser:
        if "chrome" in ua_lower and "edg" not in ua_lower:
            browser = "Chrome"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            browser = "Safari"
        elif "firefox" in ua_lower:
            browser = "Firefox"
        elif "edg" in ua_lower:
            browser = "Edge"
        else:
            browser = "Other"

    os_type = body.os
    if not os_type:
        if "mac" in ua_lower:
            os_type = "macOS"
        elif "win" in ua_lower:
            os_type = "Windows"
        elif "android" in ua_lower:
            os_type = "Android"
        elif "iphone" in ua_lower or "ipad" in ua_lower:
            os_type = "iOS"
        elif "linux" in ua_lower:
            os_type = "Linux"
        else:
            os_type = "Other"

    event_doc = {
        "event_name": body.event_name,
        "referral_code": body.referral_code,
        "utm_source": body.utm_source,
        "url": body.url,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "device": device,
        "browser": browser,
        "os": os_type,
        "created_at": datetime.now(timezone.utc)
    }

    await db.funnel_events.insert_one(event_doc)
    return {"status": "ok"}
