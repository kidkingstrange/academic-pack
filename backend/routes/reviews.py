"""
FastAPI routes for Customer Reviews & Social Proof System.
Handles public submission, WebP photo conversions, moderation, in-memory caching,
summary aggregation, and admin moderation actions.
"""
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from ..config import get_settings
from ..database import get_db
from ..services.coupon_service import issue_review_coupon
from ..services.email_service import send_email, render_template
from ..services.image_service import process_and_save_webp
from ..services.review_moderation import evaluate_review_moderation
from ..utils.review_token import hash_review_token, verify_review_token

settings = get_settings()
router = APIRouter(tags=["Reviews"])

# In-Memory TTL Cache for public endpoints (5 minutes / 300 seconds)
CACHE_TTL_SECONDS = 300
_reviews_cache = {
    "summary": {"data": None, "expires_at": 0},
    "list_default": {"data": None, "expires_at": 0},
}


def invalidate_reviews_cache():
    _reviews_cache["summary"] = {"data": None, "expires_at": 0}
    _reviews_cache["list_default"] = {"data": None, "expires_at": 0}


# ── Public Review Form Serving ────────────────────────────────────────────────
@router.get("/review/{token}", response_class=HTMLResponse)
async def serve_review_page(token: str, db=Depends(get_db)):
    """
    Validates review token and renders the frontend review submission page.
    """
    payload = verify_review_token(token)
    if not payload:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html lang="en">
            <head><meta charset="UTF-8"><title>Invalid Review Link</title>
            <style>body{background:#0d0f14;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
            .box{max-width:440px;background:#161922;padding:36px;border-radius:14px;border:1px solid rgba(255,255,255,0.1);text-align:center;}
            h2{color:#f87171;margin-bottom:12px;}p{color:#94a3b8;line-height:1.6;}a{color:#d4a63a;text-decoration:none;font-weight:700;}
            </style></head>
            <body>
            <div class="box">
              <h2>Invalid or Expired Link</h2>
              <p>This review request link is either invalid or has been modified. Please use the direct link sent to your email.</p>
              <p><a href="/">&larr; Back to Homepage</a></p>
            </div></body></html>
            """,
            status_code=400,
        )

    # Check if this purchase already submitted a review
    token_hash = hash_review_token(token)
    existing = await db.reviews.find_one({"customer_token_hash": token_hash})
    if existing:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html lang="en">
            <head><meta charset="UTF-8"><title>Review Already Received</title>
            <style>body{background:#0d0f14;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
            .box{max-width:460px;background:#161922;padding:36px;border-radius:14px;border:1px solid rgba(255,255,255,0.1);text-align:center;}
            h2{color:#4ade80;margin-bottom:12px;}p{color:#94a3b8;line-height:1.6;}a{color:#d4a63a;text-decoration:none;font-weight:700;}
            </style></head>
            <body>
            <div class="box">
              <h2>Review Already Submitted! 🎉</h2>
              <p>Thank you! We have already received your review for this purchase. Check your email inbox for your 20% discount gift code.</p>
              <p><a href="/">&larr; Back to Homepage</a></p>
            </div></body></html>
            """,
            status_code=200,
        )

    # Load review.html template file from frontend
    review_html_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "review.html"
    if review_html_path.exists():
        html_content = review_html_path.read_text(encoding="utf-8")
        # Pre-fill customer name/email into the client template
        html_content = html_content.replace("{{TOKEN}}", token)
        html_content = html_content.replace("{{CUSTOMER_NAME}}", payload.get("name", ""))
        html_content = html_content.replace("{{CUSTOMER_EMAIL}}", payload.get("email", ""))
        return HTMLResponse(content=html_content)

    return HTMLResponse(content="<h1>Review page template not found</h1>", status_code=500)


# ── Review Submission API ─────────────────────────────────────────────────────
@router.post("/api/reviews")
async def submit_review(
    token: str = Form(...),
    rating: int = Form(...),
    text: str = Form(...),
    display_name: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db=Depends(get_db),
):
    """
    Submits a verified customer review.
    Validates token, processes optional photo into WebP, applies moderation,
    stores in MongoDB, and dispatches a single-use 20% coupon.
    """
    # 1. Validate Token
    payload = verify_review_token(token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired review token.")

    email = payload["email"]
    name = payload.get("name", "Student")
    ref = payload.get("ref")
    token_hash = hash_review_token(token)

    # 2. Check for duplicate submission
    existing = await db.reviews.find_one({"customer_token_hash": token_hash})
    if existing:
        raise HTTPException(status_code=400, detail="A review has already been submitted for this purchase.")

    # 3. Validate Inputs
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=422, detail="Rating must be an integer between 1 and 5.")

    cleaned_text = (text or "").strip()
    if len(cleaned_text) < 10:
        raise HTTPException(status_code=422, detail="Please provide a review of at least 10 characters.")

    # 4. Handle Optional Photo Upload (Convert to WebP)
    photo_url = None
    if photo and photo.filename:
        photo_bytes = await photo.read()
        success, url, err = process_and_save_webp(photo_bytes)
        if not success:
            raise HTTPException(status_code=400, detail=err or "Invalid image file.")
        photo_url = url

    # 5. Hybrid Moderation
    approved, flag_reason = evaluate_review_moderation(rating, cleaned_text)

    # 6. Save Review to MongoDB
    now = datetime.now(timezone.utc)
    final_display_name = (display_name or "").strip() or name

    review_doc = {
        "customer_token_hash": token_hash,
        "payment_reference": ref,
        "email": email,
        "name": final_display_name,
        "rating": rating,
        "text": cleaned_text,
        "photo_url": photo_url,
        "date": now,
        "approved": approved,
        "flag_reason": flag_reason,
        "source": "auto",
        "created_at": now,
    }

    insert_result = await db.reviews.insert_one(review_doc)
    review_id = str(insert_result.inserted_id)

    # 7. Invalidate In-Memory Caches
    invalidate_reviews_cache()

    # 8. Issue 20% Discount Incentive
    coupon_code = await issue_review_coupon(db, email=email, name=final_display_name)

    # 9. Notify Admin if manual moderation is needed
    if not approved:
        try:
            alert_html = render_template(
                "review_admin_alert.html",
                name=final_display_name,
                email=email,
                rating=rating,
                review_text=cleaned_text,
                flag_reason=flag_reason,
                photo_url=photo_url,
                app_url=settings.APP_URL,
                admin_dashboard_url=f"{settings.APP_URL}/admin/dashboard",
            )
            await send_email(
                settings.ADMIN_EMAIL,
                f"⚠️ Review Pending Moderation ({rating} Stars) — {final_display_name}",
                alert_html,
            )
        except Exception as alert_err:
            print(f"⚠️ Failed to send review admin alert: {alert_err}")

    return {
        "success": True,
        "message": "Thank you! Your review has been successfully recorded.",
        "review_id": review_id,
        "approved": approved,
        "coupon_code": coupon_code,
    }


# ── Public Reviews List (with In-Memory TTL Caching) ───────────────────────────
@router.get("/api/reviews")
async def list_reviews(
    approved: bool = Query(True),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: str = Query("-date"),
    db=Depends(get_db),
):
    """
    Returns approved reviews for display on sales landing pages.
    Includes in-memory TTL caching for default requests.
    """
    now_ts = time.time()

    # Use cache for standard default query (approved=True, limit=20, offset=0, sort=-date)
    is_default_query = (approved is True and limit == 20 and offset == 0 and sort == "-date")
    if is_default_query and _reviews_cache["list_default"]["data"] and now_ts < _reviews_cache["list_default"]["expires_at"]:
        return _reviews_cache["list_default"]["data"]

    sort_order = -1 if sort.startswith("-") else 1
    sort_field = sort.lstrip("-")
    if sort_field not in ("date", "rating", "created_at"):
        sort_field = "date"

    query = {"approved": approved}
    cursor = db.reviews.find(query).sort(sort_field, sort_order).skip(offset).limit(limit)

    items = []
    async for r in cursor:
        items.append({
            "id": str(r["_id"]),
            "rating": r.get("rating", 5),
            "text": r.get("text", ""),
            "name": r.get("name", "Verified Student"),
            "photo_url": r.get("photo_url"),
            "date": r.get("date", r.get("created_at", datetime.now(timezone.utc))).isoformat(),
        })

    total = await db.reviews.count_documents(query)

    response_data = {
        "reviews": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + len(items)) < total,
    }

    if is_default_query:
        _reviews_cache["list_default"] = {
            "data": response_data,
            "expires_at": now_ts + CACHE_TTL_SECONDS,
        }

    return response_data


# ── Public Summary Aggregation (with In-Memory TTL Caching) ───────────────────
@router.get("/api/reviews/summary")
async def get_reviews_summary(db=Depends(get_db)):
    """
    Returns aggregated stats: average rating, total count, and star breakdown.
    Cached for 5 minutes.
    """
    now_ts = time.time()
    if _reviews_cache["summary"]["data"] and now_ts < _reviews_cache["summary"]["expires_at"]:
        return _reviews_cache["summary"]["data"]

    pipeline = [
        {"$match": {"approved": True}},
        {
            "$group": {
                "_id": "$rating",
                "count": {"$sum": 1},
            }
        },
    ]

    breakdown = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_reviews = 0
    sum_ratings = 0

    cursor = db.reviews.aggregate(pipeline)
    async for doc in cursor:
        r = doc.get("_id")
        cnt = doc.get("count", 0)
        if isinstance(r, int) and 1 <= r <= 5:
            breakdown[r] = cnt
            total_reviews += cnt
            sum_ratings += r * cnt

    avg_rating = round(sum_ratings / total_reviews, 1) if total_reviews > 0 else 5.0

    summary_data = {
        "average_rating": avg_rating,
        "total_reviews": total_reviews,
        "breakdown": breakdown,
    }

    _reviews_cache["summary"] = {
        "data": summary_data,
        "expires_at": now_ts + CACHE_TTL_SECONDS,
    }

    return summary_data


# ── Admin Moderation Endpoints ────────────────────────────────────────────────
@router.post("/api/admin/reviews/{review_id}/approve")
async def admin_approve_review(review_id: str, db=Depends(get_db)):
    """
    Admin endpoint to manually approve a review.
    """
    try:
        oid = ObjectId(review_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid review ID")

    res = await db.reviews.update_one({"_id": oid}, {"$set": {"approved": True, "moderated_at": datetime.now(timezone.utc)}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")

    invalidate_reviews_cache()
    return {"success": True, "message": "Review approved successfully"}


@router.post("/api/admin/reviews/{review_id}/reject")
async def admin_reject_review(review_id: str, db=Depends(get_db)):
    """
    Admin endpoint to manually reject/hide a review.
    """
    try:
        oid = ObjectId(review_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid review ID")

    res = await db.reviews.update_one({"_id": oid}, {"$set": {"approved": False, "moderated_at": datetime.now(timezone.utc)}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")

    invalidate_reviews_cache()
    return {"success": True, "message": "Review rejected successfully"}
