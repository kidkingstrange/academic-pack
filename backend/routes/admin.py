"""
Admin routes — login, customers, payments, analytics, product upload.
All routes require admin JWT.
"""
import asyncio
import os, shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from bson import ObjectId
from ..middleware.auth import require_admin
from ..utils.security import verify_password, hash_password, create_access_token
from ..database import get_db
from ..config import get_settings
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from ..schemas.schemas import AdminLoginRequest, TokenResponse
from ..services.affiliate_health_service import compute_affiliate_health

router = APIRouter(prefix="/api/admin", tags=["admin"])
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
async def admin_login(body: AdminLoginRequest, db=Depends(get_db)):
    """Admin login — returns JWT with role=admin."""
    # Check against env-configured admin or DB
    if body.email == settings.ADMIN_EMAIL and body.password == settings.ADMIN_PASSWORD:
        token = create_access_token({"sub": "admin", "email": body.email, "role": "admin"})
        return TokenResponse(access_token=token)

    # Also check DB admin_accounts
    admin = await db.admin_accounts.find_one({"email": body.email.lower()})
    if not admin or not verify_password(body.password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(admin["_id"]), "email": admin["email"], "role": "admin"})
    await db.admin_accounts.update_one({"_id": admin["_id"]}, {"$set": {"last_login": datetime.now(timezone.utc)}})
    return TokenResponse(access_token=token)


@router.get("/analytics")
async def get_analytics(period: str = "all", current_user=Depends(require_admin), db=Depends(get_db)):
    """Dashboard summary analytics."""
    now = datetime.now(timezone.utc)
    start_date = None
    end_date = None

    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "yesterday":
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif period == "7days":
        start_date = now - timedelta(days=7)
    elif period == "30days":
        start_date = now - timedelta(days=30)

    # Base match queries
    match_query = {"status": "success"}
    lead_query = {}
    sub_query = {"is_active": True}

    if start_date:
        match_query["verified_at"] = {"$gte": start_date}
        lead_query["created_at"] = {"$gte": start_date}
        sub_query["subscribed_at"] = {"$gte": start_date}

    if end_date:
        match_query.setdefault("verified_at", {})["$lt"] = end_date
        lead_query.setdefault("created_at", {})["$lt"] = end_date
        sub_query.setdefault("subscribed_at", {})["$lt"] = end_date

    total_sales = await db.payments.count_documents(match_query)
    total_leads = await db.leads.count_documents(lead_query)
    total_subscribers = await db.subscribers.count_documents(sub_query)
    pending_emails = await db.email_queue.count_documents({"status": {"$in": ["pending", "retry"]}})

    # Revenue
    pipeline = [{"$match": match_query}, {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
    rev_result = await db.payments.aggregate(pipeline).to_list(1)
    total_revenue = rev_result[0]["total"] if rev_result else 0

    # Conversion rate
    conversion_rate = (total_sales / total_leads * 100) if total_leads > 0 else 0

    # Downloads today
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    downloads_today = await db.downloads.count_documents({"downloaded_at": {"$gte": today_start}})

    # Recent sales (using match_query)
    recent_sales = await db.payments.find(
        match_query,
        {"_id": 0, "name": 1, "email": 1, "amount": 1, "verified_at": 1, "reference": 1}
    ).sort("verified_at", -1).limit(10).to_list(10)

    return {
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "total_leads": total_leads,
        "conversion_rate": round(conversion_rate, 1),
        "total_subscribers": total_subscribers,
        "pending_emails": pending_emails,
        "downloads_today": downloads_today,
        "recent_sales": recent_sales,
    }


# ── Dashboard tab data endpoints ────────────────────────────────────────────
# These back the 4 tabs in the rebuilt admin dashboard UI (frontend/admin/
# dashboard.html). The UI was rewritten to call these paths at some point
# without these routes ever being built — every tab 404'd. Reuses the same
# aggregation logic already proven in the routes above / routes/affiliates.py
# rather than inventing new logic.
@router.get("/analytics/overview")
async def get_analytics_overview(period: str = "all", current_user=Depends(require_admin), db=Depends(get_db)):
    now = datetime.now(timezone.utc)
    start_date = None
    end_date = None
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "yesterday":
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif period == "7days":
        start_date = now - timedelta(days=7)
    elif period == "30days":
        start_date = now - timedelta(days=30)
    elif period == "this_month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    match_query = {"status": "success"}
    lead_query = {}
    if start_date:
        match_query["verified_at"] = {"$gte": start_date}
        lead_query["created_at"] = {"$gte": start_date}
    if end_date:
        match_query.setdefault("verified_at", {})["$lt"] = end_date
        lead_query.setdefault("created_at", {})["$lt"] = end_date

    total_sales = await db.payments.count_documents(match_query)
    total_leads = await db.leads.count_documents(lead_query)
    conversion_rate = (total_sales / total_leads * 100) if total_leads > 0 else 0

    pipeline = [{"$match": match_query}, {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
    rev_result = await db.payments.aggregate(pipeline).to_list(1)
    total_revenue = rev_result[0]["total"] if rev_result else 0
    aov = (total_revenue / total_sales) if total_sales > 0 else 0

    # Fixed rollup windows — independent of the period selector, since these
    # are labeled as specific windows (Today/Week/Month), not filtered views.
    async def revenue_since(since):
        pipe = [{"$match": {"status": "success", "verified_at": {"$gte": since}}},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
        result = await db.payments.aggregate(pipe).to_list(1)
        return result[0]["total"] if result else 0

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    today_revenue = await revenue_since(today_start)
    week_revenue = await revenue_since(week_start)
    month_revenue = await revenue_since(month_start)

    # Commission owed across all affiliates — tracking only, no automation.
    owed_pipeline = [
        {"$group": {
            "_id": None,
            "earned": {"$sum": "$commission_amount"},
            "paid": {"$sum": {"$cond": [{"$eq": ["$commission_status", "paid"]}, "$commission_amount", 0]}},
        }}
    ]
    owed_result = await db.referrals.aggregate(owed_pipeline).to_list(1)
    commission_owed = (owed_result[0]["earned"] - owed_result[0]["paid"]) if owed_result else 0

    # 30-day daily revenue trend for the chart — a real aggregation, not AI.
    thirty_days_ago = now - timedelta(days=30)
    trend_pipeline = [
        {"$match": {"status": "success", "verified_at": {"$gte": thirty_days_ago}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$verified_at"}},
            "revenue": {"$sum": "$amount"},
        }},
        {"$sort": {"_id": 1}},
    ]
    daily_trends = await db.payments.aggregate(trend_pipeline).to_list(31)

    recent_transactions = await db.payments.find(
        match_query, {"_id": 0, "name": 1, "email": 1, "amount": 1, "verified_at": 1, "reference": 1, "status": 1}
    ).sort("verified_at", -1).limit(10).to_list(10)

    recent_leads = await db.leads.find(
        lead_query, {"_id": 0, "email": 1, "source": 1, "created_at": 1}
    ).sort("created_at", -1).limit(10).to_list(10)

    return {
        "total_revenue": total_revenue,
        "today_revenue": today_revenue,
        "week_revenue": week_revenue,
        "month_revenue": month_revenue,
        "total_sales": total_sales,
        "aov": round(aov, 2),
        "conversion_rate": round(conversion_rate, 1),
        "pending_payouts": commission_owed,
        # No AI-generated insights — out of scope. Kept as an empty list so
        # the frontend's existing render call doesn't error; the panel
        # itself is a Phase 1 design decision (keep/remove), not this fix.
        "ai_insights": [],
        "daily_trends": daily_trends,
        "recent_transactions": recent_transactions,
        "recent_leads": recent_leads,
    }


@router.get("/analytics/sales")
async def get_analytics_sales(
    period: str = "all",
    start_date: str = None,
    end_date: str = None,
    current_user=Depends(require_admin), db=Depends(get_db),
):
    """
    start_date/end_date (ISO "YYYY-MM-DD") give a genuine arbitrary date
    range — e.g. reconciling a specific week — and take precedence over
    the period presets when provided, since presets alone can't answer
    "show me sales between the 3rd and the 10th".
    """
    now = datetime.now(timezone.utc)
    query = {}

    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date:
            date_filter["$lt"] = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        query["created_at"] = date_filter
    elif period == "today":
        query["created_at"] = {"$gte": now.replace(hour=0, minute=0, second=0, microsecond=0)}
    elif period == "yesterday":
        y_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        query["created_at"] = {"$gte": y_start, "$lt": y_start + timedelta(days=1)}
    elif period == "7days":
        query["created_at"] = {"$gte": now - timedelta(days=7)}
    elif period == "30days":
        query["created_at"] = {"$gte": now - timedelta(days=30)}
    elif period == "this_month":
        query["created_at"] = {"$gte": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)}

    transactions = await db.payments.find(
        query, {"gateway_response": 0}
    ).sort("created_at", -1).limit(500).to_list(500)
    for t in transactions:
        t["id"] = str(t.pop("_id"))
        if "user_id" in t and t["user_id"]:
            t["user_id"] = str(t["user_id"])

    return {"transactions": transactions}


@router.get("/analytics/customers")
async def get_analytics_customers(
    search: str = "",
    start_date: str = None,
    end_date: str = None,
    page: int = 1,
    limit: int = 20,
    current_user=Depends(require_admin), db=Depends(get_db),
):
    query = {"role": "customer"}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date:
            date_filter["$lt"] = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        query["created_at"] = date_filter

    # Fetch all matching emails to compute aggregates globally in one pass
    all_matching = await db.users.find(query, {"email": 1}).to_list(100000)
    emails = [u["email"] for u in all_matching]
    total = len(emails)

    if not emails:
        return {
            "total": 0,
            "repeat_purchase_rate": 0,
            "avg_clv": 0,
            "customers": [],
            "page": page,
            "pages": 0
        }

    # Bulk query to count/sum payments for all matched users
    pipeline = [
        {"$match": {"email": {"$in": emails}, "status": "success"}},
        {"$group": {
            "_id": "$email",
            "total_spent": {"$sum": "$amount"},
            "purchases_count": {"$sum": 1}
        }}
    ]
    payments_results = await db.payments.aggregate(pipeline).to_list(None)
    payments_map = {r["_id"]: r for r in payments_results}

    # Calculate global metrics
    total_spent_all = sum(r["total_spent"] for r in payments_results)
    repeat_count = sum(1 for r in payments_results if r["purchases_count"] > 1)
    repeat_purchase_rate = round((repeat_count / total * 100), 1)
    avg_clv = round((total_spent_all / total), 2)

    # Fetch paginated list
    skip = (page - 1) * limit
    customers = await db.users.find(query, {"password_hash": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    out = []
    for c in customers:
        email = c["email"]
        stats = payments_map.get(email, {"total_spent": 0, "purchases_count": 0})
        out.append({
            "created_at": c["created_at"],
            "name": c.get("name", ""),
            "email": email,
            "total_spent": stats.get("total_spent", 0),
            "purchases_count": stats.get("purchases_count", 0),
        })

    return {
        "total": total,
        "repeat_purchase_rate": repeat_purchase_rate,
        "avg_clv": avg_clv,
        "customers": out,
        "page": page,
        "pages": -(-total // limit)
    }


@router.get("/analytics/affiliates")
async def get_analytics_affiliates(current_user=Depends(require_admin), db=Depends(get_db)):
    """Same aggregation as GET /api/admin/affiliates (routes/affiliates.py),
    reused here rather than duplicated logic drifting — backs the
    Affiliates Engine tab, which was calling a path that never existed."""
    affiliates = await db.affiliates.find({}).sort("created_at", -1).to_list(500)

    click_counts = {
        row["_id"]: row["count"]
        for row in await db.referral_clicks.aggregate([
            {"$group": {"_id": "$affiliate_code", "count": {"$sum": 1}}}
        ]).to_list(500)
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
                    "$sum": {"$cond": [{"$eq": ["$commission_status", "paid"]}, "$commission_amount", 0]}
                },
            }}
        ]).to_list(500)
    }

    out = []
    for a in affiliates:
        code = a["code"]
        stats = referral_stats.get(code, {})
        earned = stats.get("commission_earned", 0) or 0
        paid = stats.get("commission_paid", 0) or 0
        out.append({
            "id": str(a["_id"]),
            "code": code,
            "name": a["name"],
            "email": a["email"],
            "active": a.get("active", True),
            "source": a.get("source", "admin_created"),
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
        })
    return {"affiliates": out}


@router.get("/analytics/affiliate-health")
async def get_affiliate_health(current_user=Depends(require_admin), db=Depends(get_db)):
    """
    Affiliate Program Health summary — MAA (primary metric), activation
    rate, revenue concentration, retention, and the never-activated list
    (the actionable "these people need a nudge" view).
    """
    return await compute_affiliate_health(db)


@router.get("/customers")
async def list_customers(
    page: int = 1, limit: int = 20,
    current_user=Depends(require_admin), db=Depends(get_db)
):
    skip = (page - 1) * limit
    customers = await db.users.find(
        {"role": "customer"},
        {"password_hash": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.users.count_documents({"role": "customer"})

    for c in customers:
        c["id"] = str(c.pop("_id"))
    return {"customers": customers, "total": total, "page": page, "pages": -(-total // limit)}


@router.get("/payments")
async def list_payments(
    page: int = 1, limit: int = 200,
    current_user=Depends(require_admin), db=Depends(get_db)
):
    skip = (page - 1) * limit
    payments = await db.payments.find(
        {}, {"gateway_response": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.payments.count_documents({})

    for p in payments:
        p["id"] = str(p.pop("_id"))
        if "user_id" in p and p["user_id"]:
            p["user_id"] = str(p["user_id"])
    return {"payments": payments, "total": total, "page": page}


@router.get("/subscribers")
async def list_subscribers(
    page: int = 1, limit: int = 20,
    current_user=Depends(require_admin), db=Depends(get_db)
):
    skip = (page - 1) * limit
    subs = await db.subscribers.find({}).sort("subscribed_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.subscribers.count_documents({})
    for s in subs:
        s["id"] = str(s.pop("_id"))
    return {"subscribers": subs, "total": total, "page": page}


@router.get("/email-queue")
async def get_email_queue(
    status: str = None, page: int = 1, limit: int = 20,
    current_user=Depends(require_admin), db=Depends(get_db)
):
    query = {}
    if status:
        query["status"] = status
    skip = (page - 1) * limit
    items = await db.email_queue.find(query).sort("scheduled_at", 1).skip(skip).limit(limit).to_list(limit)
    total = await db.email_queue.count_documents(query)
    for i in items:
        i["id"] = str(i.pop("_id"))
        i["subscriber_id"] = str(i["subscriber_id"])
    return {"queue": items, "total": total, "page": page}


@router.post("/products")
async def upload_product(
    title: str = Form(...),
    description: str = Form(...),
    order: int = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    """Upload a new PDF product."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in file.filename)
    file_path = Path(settings.UPLOADS_DIR) / safe_name
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = await db.products.insert_one({
        "title": title,
        "description": description,
        "file_path": safe_name,
        "thumbnail": None,
        "order": order,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    return {"id": str(result.inserted_id), "title": title, "message": "Product uploaded successfully"}


@router.get("/leads")
async def list_leads(
    page: int = 1, limit: int = 20,
    current_user=Depends(require_admin), db=Depends(get_db)
):
    skip = (page - 1) * limit
    leads = await db.leads.find({}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.leads.count_documents({})
    for l in leads:
        l["id"] = str(l.pop("_id"))
    return {"leads": leads, "total": total, "page": page}


# ── Deep Sales & Order Management Endpoints ─────────────────────────────────────
@router.get("/sales/{reference}/details")
async def get_sale_details(reference: str, current_user=Depends(require_admin), db=Depends(get_db)):
    """Deep inspection of a single sale: payment status, customer info, attribution, notes, and emails."""
    payment = await db.payments.find_one({"reference": reference})
    if not payment:
        # Fallback search by ID or reference
        payment = await db.payments.find_one({"$or": [{"reference": reference}, {"charge_id": reference}]})
    if not payment:
        raise HTTPException(status_code=404, detail="Sale transaction not found")

    payment["id"] = str(payment.pop("_id"))
    if payment.get("user_id"):
        payment["user_id"] = str(payment["user_id"])
    email = payment.get("email", "").lower()

    # Customer Profile Info
    customer = await db.users.find_one({"email": email}, {"password_hash": 0})
    customer_id = customer["_id"] if customer else None
    if customer:
        customer["id"] = str(customer.pop("_id"))

    # Referral Attribution
    referral = await db.referrals.find_one({"reference": reference})
    if referral:
        referral["id"] = str(referral.pop("_id"))

    # Email Queue Delivery History
    emails = await db.email_queue.find({"email": email}).sort("scheduled_at", -1).to_list(20)
    for e in emails:
        e["id"] = str(e.pop("_id"))
        if e.get("subscriber_id"):
            e["subscriber_id"] = str(e["subscriber_id"])
        if e.get("user_id"):
            e["user_id"] = str(e["user_id"])

    # Downloads Activity History — downloads are keyed by user_id, not email
    downloads = []
    if customer_id:
        downloads = await db.downloads.find({"user_id": customer_id}).sort("downloaded_at", -1).to_list(50)
        for d in downloads:
            d["id"] = str(d.pop("_id"))
            d["user_id"] = str(d["user_id"])
            if d.get("product_id"):
                d["product_id"] = str(d["product_id"])

    return {
        "payment": payment,
        "customer": customer,
        "referral": referral,
        "emails": emails,
        "downloads": downloads
    }


@router.post("/sales/{reference}/notes")
async def update_sale_notes(reference: str, payload: dict, current_user=Depends(require_admin), db=Depends(get_db)):
    """Update manual admin notes on a specific sale."""
    notes = payload.get("notes", "").strip()
    res = await db.payments.update_one({"reference": reference}, {"$set": {"admin_notes": notes, "notes_updated_at": datetime.now(timezone.utc)}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"status": "ok", "message": "Sale notes updated successfully"}


@router.post("/sales/{reference}/resend-email")
async def resend_sale_welcome_email(reference: str, current_user=Depends(require_admin), db=Depends(get_db)):
    """Re-queue access email delivery for a customer."""
    payment = await db.payments.find_one({"reference": reference})
    if not payment:
        raise HTTPException(status_code=404, detail="Transaction not found")

    email = payment.get("email", "").lower()
    name = payment.get("name", "Valued Customer")

    user = await db.users.find_one({"email": email})
    token = user.get("library_access_token") if user else None
    if not token:
        raise HTTPException(status_code=409, detail="Customer has no library access token yet — payment may not be fully completed.")

    sub = await db.subscribers.find_one({"email": email})
    unsub_token = sub.get("unsubscribe_token", "") if sub else ""

    # Same document shape complete_payment() inserts for a real "welcome"
    # email (see services/payment_completion.py) — matching it exactly so
    # this resend is indistinguishable from a normal one to the scheduler.
    welcome_item = {
        "kind": "welcome",
        "user_id": user["_id"] if user else None,
        "email": email,
        "name": name,
        "access_token": token,
        "unsubscribe_token": unsub_token,
        "scheduled_at": datetime.now(timezone.utc),
        "status": "pending",
        "retry_count": 0,
        "sent_at": None,
        "error": None,
    }
    await db.email_queue.insert_one(welcome_item)

    # Fire-and-forget immediate processing attempt — same pattern used
    # everywhere else in this app (see payment_completion.py,
    # affiliate_public.py) rather than waiting for the 5-minute scheduler
    # tick. process_email_queue() is already lock-protected against
    # overlapping with the scheduler's own tick.
    from ..workers.email_scheduler import process_email_queue
    asyncio.create_task(process_email_queue())

    return {"status": "ok", "message": f"Welcome email queued for re-delivery to {email}"}


@router.post("/sales/{reference}/refund")
async def process_sale_refund(reference: str, payload: dict, current_user=Depends(require_admin), db=Depends(get_db)):
    """Mark a sale transaction as refunded."""
    reason = payload.get("reason", "Refunded by admin").strip()
    res = await db.payments.update_one(
        {"reference": reference},
        {"$set": {"status": "refunded", "refund_reason": reason, "refunded_at": datetime.now(timezone.utc)}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"status": "ok", "message": f"Transaction {reference} marked as refunded."}


# ── Deep Customer Profile Management Endpoints ────────────────────────────────
@router.get("/customers/{email}/profile")
async def get_customer_profile(email: str, current_user=Depends(require_admin), db=Depends(get_db)):
    """Deep customer 360-degree profile inspector."""
    email_clean = email.lower().strip()
    customer = await db.users.find_one({"email": email_clean}, {"password_hash": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer profile not found")

    customer_id = customer["_id"]
    customer["id"] = str(customer.pop("_id"))

    # Purchases & Payments History
    payments = await db.payments.find({"email": email_clean}).sort("verified_at", -1).to_list(100)
    total_spent = 0
    for p in payments:
        p["id"] = str(p.pop("_id"))
        if p.get("user_id"):
            p["user_id"] = str(p["user_id"])
        if p.get("status") == "success":
            total_spent += p.get("amount", 0)

    # Downloads Activity Log — downloads are keyed by user_id, not email
    downloads = await db.downloads.find({"user_id": customer_id}).sort("downloaded_at", -1).to_list(100)
    for d in downloads:
        d["id"] = str(d.pop("_id"))
        d["user_id"] = str(d["user_id"])
        if d.get("product_id"):
            d["product_id"] = str(d["product_id"])

    # Email Delivery Logs
    emails = await db.email_queue.find({"email": email_clean}).sort("scheduled_at", -1).to_list(50)
    for e in emails:
        e["id"] = str(e.pop("_id"))
        if e.get("subscriber_id"):
            e["subscriber_id"] = str(e["subscriber_id"])
        if e.get("user_id"):
            e["user_id"] = str(e["user_id"])

    return {
        "customer": customer,
        "total_spent": total_spent,
        "purchases": payments,
        "downloads": downloads,
        "emails": emails
    }


@router.post("/customers/{email}/tags")
async def update_customer_tags(email: str, payload: dict, current_user=Depends(require_admin), db=Depends(get_db)):
    """Update customer segmentation tags (e.g. VIP, High Value, Repeat Buyer)."""
    tags = payload.get("tags", [])
    if not isinstance(tags, list):
        tags = [str(tags)]
    res = await db.users.update_one({"email": email.lower()}, {"$set": {"tags": tags}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"status": "ok", "tags": tags}


@router.post("/customers/{email}/notes")
async def update_customer_notes(email: str, payload: dict, current_user=Depends(require_admin), db=Depends(get_db)):
    """Save manual admin notes on customer account."""
    notes = payload.get("notes", "").strip()
    res = await db.users.update_one({"email": email.lower()}, {"$set": {"notes": notes}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"status": "ok", "message": "Customer notes updated"}


# ── Affiliate Payout & Management Endpoints ────────────────────────────────────
@router.post("/affiliates/{code}/mark-payout")
async def mark_affiliate_payout(code: str, payload: dict, current_user=Depends(require_admin), db=Depends(get_db)):
    """Mark pending commissions for an affiliate code as paid out."""
    payout_ref = payload.get("payout_reference", f"PAYOUT-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    res = await db.referrals.update_many(
        {"affiliate_code": code, "commission_status": {"$ne": "paid"}},
        {"$set": {"commission_status": "paid", "payout_reference": payout_ref, "paid_at": datetime.now(timezone.utc)}}
    )
    return {"status": "ok", "modified_count": res.modified_count, "payout_reference": payout_ref}


@router.post("/affiliates/{code}/status")
async def toggle_affiliate_status(code: str, payload: dict, current_user=Depends(require_admin), db=Depends(get_db)):
    """Activate or suspend an affiliate code."""
    active = bool(payload.get("active", True))
    res = await db.affiliates.update_one({"code": code}, {"$set": {"active": active, "updated_at": datetime.now(timezone.utc)}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Affiliate code not found")
    return {"status": "ok", "code": code, "active": active}


# ── Subscriptions Administration ──────────────────────────────────────────────
@router.get("/subscriptions")
async def admin_get_subscriptions(
    search: Optional[str] = None,
    status: Optional[str] = None,
    current_user=Depends(require_admin),
    db=Depends(get_db)
):
    query = {}
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"customer_name": {"$regex": search, "$options": "i"}},
            {"customer_email": {"$regex": search, "$options": "i"}}
        ]

    subs = await db.subscriptions.find(query).sort("created_at", -1).to_list(100)
    
    # Resolve offer names and prices
    resolved_subs = []
    for sub in subs:
        offer = await db.offers.find_one({"_id": sub["offer_id"]})
        resolved_subs.append({
            "id": str(sub["_id"]),
            "customer_name": sub["customer_name"],
            "customer_email": sub["customer_email"],
            "customer_phone": sub.get("customer_phone", ""),
            "status": sub["status"],
            "card_last4": sub.get("card_last4", "••••"),
            "card_brand": sub.get("card_brand", "Card"),
            "next_charge_date": sub["next_charge_date"].isoformat() if sub.get("next_charge_date") else None,
            "created_at": sub["created_at"].isoformat() if sub.get("created_at") else None,
            "offer_name": offer["name"] if offer else "Unknown Plan",
            "offer_price": offer["price"] if offer else 0
        })

    return resolved_subs


@router.get("/subscriptions/kpis")
async def admin_get_subscriptions_kpis(
    current_user=Depends(require_admin),
    db=Depends(get_db)
):
    active_count = await db.subscriptions.count_documents({"status": "active"})
    past_due_count = await db.subscriptions.count_documents({"status": "past_due"})
    cancelled_count = await db.subscriptions.count_documents({"status": "cancelled"})

    # Compute MRR
    # Sum of price of all active and past_due subscriptions
    mrr = 0
    subs = await db.subscriptions.find({"status": {"$in": ["active", "past_due"]}}).to_list(1000)
    for sub in subs:
        offer = await db.offers.find_one({"_id": sub["offer_id"]})
        if offer:
            mrr += offer["price"]

    return {
        "mrr": mrr,
        "active_count": active_count,
        "past_due_count": past_due_count,
        "cancelled_count": cancelled_count
    }


# ── Schemas for Team Member Management ──────────────────────────────────────────
class SalesRepCreateRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class SalesRepPasswordRequest(BaseModel):
    password: str

# ── Endpoints for Team Member Management ────────────────────────────────────────
@router.get("/sales-reps")
async def list_sales_reps(current_user=Depends(require_admin), db=Depends(get_db)):
    reps = await db.sales_reps.find({}).sort("created_at", -1).to_list(1000)
    out = []
    for r in reps:
        # Leads count
        leads_count = await db.sales_leads.count_documents({"sales_rep_id": r["_id"]})
        # Subscriptions count
        subs_count = await db.subscriptions.count_documents({"sales_rep_id": r["_id"]})
        out.append({
            "id": str(r["_id"]),
            "name": r.get("name", ""),
            "email": r.get("email", ""),
            "active": r.get("active", True),
            "created_at": r.get("created_at"),
            "leads_count": leads_count,
            "subs_count": subs_count
        })
    return {"sales_reps": out}

@router.post("/sales-reps")
async def create_sales_rep(body: SalesRepCreateRequest, current_user=Depends(require_admin), db=Depends(get_db)):
    existing = await db.sales_reps.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Team member already exists")
    
    rep = {
        "name": body.name,
        "email": body.email.lower(),
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(timezone.utc),
        "active": True
    }
    await db.sales_reps.insert_one(rep)
    return {"status": "ok", "message": "Team member registered successfully"}

@router.post("/sales-reps/{rep_id}/status")
async def toggle_sales_rep_status(rep_id: str, payload: dict, current_user=Depends(require_admin), db=Depends(get_db)):
    active = bool(payload.get("active", True))
    res = await db.sales_reps.update_one({"_id": ObjectId(rep_id)}, {"$set": {"active": active}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Team member not found")
    return {"status": "ok", "active": active}

@router.post("/sales-reps/{rep_id}/password")
async def change_sales_rep_password(rep_id: str, body: SalesRepPasswordRequest, current_user=Depends(require_admin), db=Depends(get_db)):
    res = await db.sales_reps.update_one(
        {"_id": ObjectId(rep_id)},
        {"$set": {"password_hash": hash_password(body.password)}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Team member not found")
    return {"status": "ok", "message": "Password updated successfully"}

@router.delete("/sales-reps/{rep_id}")
async def delete_sales_rep(rep_id: str, current_user=Depends(require_admin), db=Depends(get_db)):
    res = await db.sales_reps.delete_one({"_id": ObjectId(rep_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Team member not found")
    return {"status": "ok", "message": "Team member deleted"}


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL SEQUENCE MONITORING ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

_SEQ_DAY_OFFSETS = [
    0, 3, 7, 10, 14, 17, 21, 24, 28, 31, 35, 38,
    42, 45, 49, 52, 56, 59, 63, 66, 70, 73, 77, 80,
    84, 87, 91, 94, 98, 101, 105, 108, 112, 115, 119, 122,
    126, 129, 133, 136, 140, 143, 147, 150, 154, 157, 161, 164,
    168, 171, 175, 178,
]

_SEQ_SUBJECTS = [
    "You're not lazy — you just don't have the right system yet",
    "The top student in your class isn't smarter than you",
    "Your grades reflect your habits — not your potential",
    "Two students. Same exam. The only difference is what they believe about it.",
    "Every great performer you admire was once a beginner who found the right method",
    "The curiosity you had as a child didn't disappear — it was buried",
    "Your brain doesn't record like a camera — it builds like a scaffold",
    "Barbara Oakley couldn't do maths. Then she learned how the brain actually changes.",
    "You've been studying the wrong way (and it feels productive)",
    "If studying feels comfortable, something is probably wrong.",
    "Your brain processes visuals 60,000x faster than text. You're studying the slow way.",
    "You're not bad at remembering. You're bad at reviewing. Different problem.",
    "The most powerful study technique has been proven for 100+ years. You're not using it.",
    "One technique mastered beats ten techniques practised",
    "Your notes aren't the problem — what you do after is",
    "The real reason you can't focus when you study",
    "This student studied 4 hours a day and outscored the 12-hour grinders",
    "There's a point where more studying actively destroys your performance.",
    "You're not multitasking — you're just switching fast and paying the cost",
    "Your mind wanders 47% of the time. Here's what to do about it.",
    "Every unfinished task in your head is quietly draining your focus",
    "Flow is not luck. It has trigger conditions — and you can set them.",
    "You have the same 24 hours as every top student. Here's what they do differently.",
    "The world's smartest people use checklists. Here's why you should too.",
    "Motivation is the spark. You can't run an engine on sparks.",
    "You don't need more discipline — you need a smaller starting point",
    "It's not a discipline problem. It's a design problem.",
    "The gap between average and excellent isn't talent — it's one habit",
    "One habit. Twenty minutes. Every week. The results are remarkable.",
    'Every Monday is "the new start." At what point does the pattern become the problem?',
    "You already know what you should be doing. That's not the problem.",
    "Your grades are built in the moments nobody sees",
    "Working hard on the wrong things is worse than not working at all",
    "Stop blaming yourself for your grades. Fix the system upstream.",
    "The best student in the room isn't the hardest worker — they're the most strategic",
    "MIT in 12 months — and what it reveals about how you're wasting yours",
    "The most powerful career question applies to your academic life right now",
    '"Balance" is not about doing everything equally. Here\'s what it actually means.',
    "Exam anxiety has nothing to do with the exam",
    "The most pressure-proof students aren't fearless — they're prepared differently",
    "There's a kind of suffering nobody talks about — slow, invisible progress",
    "You won't notice it happening. Then one day you'll be unrecognisable.",
    "The most powerful motivation isn't external. It's a clear picture of who you're becoming.",
    "What you do in the next 90 days will still matter in 2031.",
    "A mentor doesn't do the work for you — they show you which work matters",
    "Michael Jordan had a coach. What makes you think you should do this alone?",
    "He was three failed courses in and considering dropping out. Six months later:",
    "The decision to not decide is itself a decision. And it has a price.",
    "I'm not going to sell you. I'm going to tell you the truth about why this exists.",
    "Let me show you what the before and after actually looks like.",
    "The argument against investing in yourself is made by the version of you that benefits least.",
    "One question left.",
]


def _correct_seq_position(subscribed_at, now):
    if subscribed_at is None:
        return 0
    if subscribed_at.tzinfo is None:
        subscribed_at = subscribed_at.replace(tzinfo=timezone.utc)
    days_elapsed = (now - subscribed_at).total_seconds() / 86400
    pos = 0
    for i, offset in enumerate(_SEQ_DAY_OFFSETS):
        if days_elapsed >= offset:
            pos = i + 1
        else:
            break
    return min(pos, 52)


@router.get("/sequence/overview")
async def get_sequence_overview(current_user=Depends(require_admin), db=Depends(get_db)):
    """Aggregate health KPIs for the 52-email curriculum sequence."""
    now = datetime.now(timezone.utc)
    total_enrolled = await db.subscribers.count_documents({"is_active": True})
    total_sent = await db.email_queue.count_documents({"kind": "sequence", "status": "sent"})
    total_pending = await db.email_queue.count_documents({"kind": "sequence", "status": "pending"})
    total_failed = await db.email_queue.count_documents({"kind": "sequence", "status": "failed"})
    total_retry = await db.email_queue.count_documents({"kind": "sequence", "status": "retry"})
    stuck_sending = await db.email_queue.count_documents({"status": "sending"})
    overdue_count = await db.email_queue.count_documents({
        "kind": "sequence", "status": {"$in": ["pending", "retry"]}, "scheduled_at": {"$lte": now}
    })
    last_sent_doc = await db.email_queue.find_one(
        {"kind": "sequence", "status": "sent"}, sort=[("sent_at", -1)]
    )
    last_sent_at = last_sent_doc["sent_at"].isoformat() if last_sent_doc and last_sent_doc.get("sent_at") else None

    # Fetch all active subscriber metadata in bulk to avoid N+1 queries
    subs = await db.subscribers.find({"is_active": True}, {"subscribed_at": 1}).to_list(100000)
    sub_ids = [s["_id"] for s in subs]

    # Bulk fetch sent counts for active subscribers
    pipeline = [
        {"$match": {"subscriber_id": {"$in": sub_ids}, "kind": "sequence", "status": "sent"}},
        {"$group": {"_id": "$subscriber_id", "sent_count": {"$sum": 1}}}
    ]
    sent_results = await db.email_queue.aggregate(pipeline).to_list(None)
    sent_map = {str(r["_id"]): r["sent_count"] for r in sent_results}

    stage_distribution = {}
    subscribers_behind = 0
    for sub in subs:
        correct = _correct_seq_position(sub.get("subscribed_at"), now)
        stage_distribution[correct] = stage_distribution.get(correct, 0) + 1
        
        actual = sent_map.get(str(sub["_id"]), 0)
        if actual < correct:
            subscribers_behind += 1

    stage_list = []
    for pos in sorted(stage_distribution.keys()):
        stage_list.append({
            "email_number": pos,
            "count": stage_distribution[pos],
            "day_offset": _SEQ_DAY_OFFSETS[pos - 1] if 1 <= pos <= 52 else None,
            "subject_preview": _SEQ_SUBJECTS[pos - 1][:70] if 1 <= pos <= 52 else "—",
        })

    return {
        "total_enrolled": total_enrolled,
        "total_sent": total_sent,
        "total_pending": total_pending,
        "total_failed": total_failed,
        "total_retry": total_retry,
        "overdue_count": overdue_count,
        "stuck_sending_count": stuck_sending,
        "subscribers_behind": subscribers_behind,
        "last_sent_at": last_sent_at,
        "stage_distribution": stage_list,
        "health_status": (
            "critical" if stuck_sending > 0 or total_failed > 10
            else "degraded" if subscribers_behind > 3 or total_failed > 0
            else "healthy"
        ),
    }


@router.get("/sequence/subscribers")
async def get_sequence_subscribers(
    page: int = 1,
    limit: int = 20,
    search: str = "",
    current_user=Depends(require_admin), db=Depends(get_db)
):
    """Per-subscriber sequence status table."""
    now = datetime.now(timezone.utc)
    
    query = {"is_active": True}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]

    total = await db.subscribers.count_documents(query)
    skip = (page - 1) * limit
    subs = await db.subscribers.find(query).sort("subscribed_at", -1).skip(skip).limit(limit).to_list(limit)

    # Bulk query count of sent/failed emails for just the 20 page subscribers
    sub_ids = [s["_id"] for s in subs]
    counts_pipeline = [
        {"$match": {"subscriber_id": {"$in": sub_ids}, "kind": "sequence", "status": {"$in": ["sent", "failed"]}}},
        {"$group": {
            "_id": "$subscriber_id",
            "sent_count": {"$sum": {"$cond": [{"$eq": ["$status", "sent"]}, 1, 0]}},
            "failed_count": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}}
        }}
    ]
    counts_results = await db.email_queue.aggregate(counts_pipeline).to_list(None)
    counts_map = {str(r["_id"]): r for r in counts_results}

    result = []
    for sub in subs:
        sub_id = sub["_id"]
        sub_id_str = str(sub_id)
        subscribed_at = sub.get("subscribed_at")
        correct_pos = _correct_seq_position(subscribed_at, now)
        
        stats = counts_map.get(sub_id_str, {"sent_count": 0, "failed_count": 0})
        actually_sent = stats["sent_count"]
        failed_count = stats["failed_count"]

        # Loop queries only run 20 times due to pagination limit, which is fast and O(1)
        last_sent_doc = await db.email_queue.find_one(
            {"subscriber_id": sub_id, "kind": "sequence", "status": "sent"}, sort=[("sent_at", -1)]
        )
        next_doc = await db.email_queue.find_one(
            {"subscriber_id": sub_id, "kind": "sequence", "status": {"$in": ["pending", "retry"]}},
            sort=[("scheduled_at", 1)]
        )
        next_due = None
        next_seq_num = None
        next_subject = None
        is_overdue = False
        if next_doc:
            nd = next_doc.get("scheduled_at")
            if nd:
                nd_aware = nd if nd.tzinfo else nd.replace(tzinfo=timezone.utc)
                next_due = nd_aware.isoformat()
                is_overdue = nd_aware <= now
            next_seq_num = next_doc.get("sequence_number")
            if next_seq_num and 1 <= next_seq_num <= 52:
                next_subject = _SEQ_SUBJECTS[next_seq_num - 1]
        days_elapsed = 0
        if subscribed_at:
            sa = subscribed_at if subscribed_at.tzinfo else subscribed_at.replace(tzinfo=timezone.utc)
            days_elapsed = round((now - sa).total_seconds() / 86400, 1)
        result.append({
            "subscriber_id": sub_id_str,
            "name": sub.get("name", ""),
            "email": sub.get("email", ""),
            "subscribed_at": subscribed_at.isoformat() if subscribed_at else None,
            "days_enrolled": days_elapsed,
            "correct_position": correct_pos,
            "emails_sent": actually_sent,
            "emails_behind": max(0, correct_pos - actually_sent),
            "failed_count": failed_count,
            "next_email_number": next_seq_num,
            "next_subject": next_subject,
            "next_due_at": next_due,
            "is_overdue": is_overdue,
            "is_behind": actually_sent < correct_pos,
            "status": ("overdue" if is_overdue else "behind" if actually_sent < correct_pos else "completed" if actually_sent >= 52 else "on_track"),
            "last_sent_at": last_sent_doc["sent_at"].isoformat() if last_sent_doc and last_sent_doc.get("sent_at") else None,
            "last_email_number": last_sent_doc.get("sequence_number") if last_sent_doc else None,
        })
    return {
        "subscribers": result,
        "total": total,
        "page": page,
        "pages": -(-total // limit)
    }


@router.get("/sequence/subscriber/{email_addr}")
async def get_subscriber_sequence_history(email_addr: str, current_user=Depends(require_admin), db=Depends(get_db)):
    """Full send history for one subscriber — every item in the queue."""
    sub = await db.subscribers.find_one({"email": email_addr.lower()})
    if not sub:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    items = await db.email_queue.find({"subscriber_id": sub["_id"], "kind": "sequence"}, sort=[("sequence_number", 1)]).to_list(60)
    now = datetime.now(timezone.utc)
    history = []
    for item in items:
        sa = item.get("scheduled_at")
        se = item.get("sent_at")
        history.append({
            "sequence_number": item.get("sequence_number"),
            "subject": item.get("subject", ""),
            "template": item.get("template", ""),
            "status": item.get("status"),
            "scheduled_at": sa.isoformat() if sa else None,
            "sent_at": se.isoformat() if se else None,
            "retry_count": item.get("retry_count", 0),
            "error": item.get("error"),
        })
    return {
        "subscriber": {"name": sub.get("name"), "email": sub.get("email"), "subscribed_at": sub["subscribed_at"].isoformat() if sub.get("subscribed_at") else None, "correct_position": _correct_seq_position(sub.get("subscribed_at"), now)},
        "history": history, "total": len(history),
    }


@router.post("/sequence/resend/{email_addr}")
async def resend_subscriber_sequence_email(email_addr: str, current_user=Depends(require_admin), db=Depends(get_db)):
    """Manually reschedule the next failed/stuck sequence email for a subscriber."""
    sub = await db.subscribers.find_one({"email": email_addr.lower()})
    if not sub:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    now = datetime.now(timezone.utc)
    stuck = await db.email_queue.find_one(
        {"subscriber_id": sub["_id"], "kind": "sequence", "status": {"$in": ["failed", "retry"]}},
        sort=[("sequence_number", 1)]
    )
    if not stuck:
        return {"status": "ok", "message": "No failed or stuck sequence emails found for this subscriber"}
    await db.email_queue.update_one(
        {"_id": stuck["_id"]},
        {"$set": {"status": "pending", "retry_count": 0, "error": None, "scheduled_at": now}}
    )
    return {"status": "ok", "message": f"Re-queued sequence email #{stuck.get('sequence_number')} for {email_addr}. Will send within 5 minutes."}
