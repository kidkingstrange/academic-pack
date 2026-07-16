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
    customers = await db.users.find(query, {"password_hash": 0}).sort("created_at", -1).limit(500).to_list(500)
    total = len(customers)

    out = []
    repeat_count = 0
    total_spent_all = 0
    for c in customers:
        email = c["email"]
        payments = await db.payments.find(
            {"email": email, "status": "success"}, {"_id": 0, "amount": 1}
        ).to_list(1000)
        total_spent = sum(p.get("amount", 0) or 0 for p in payments)
        total_spent_all += total_spent
        if len(payments) > 1:
            repeat_count += 1
        out.append({
            "created_at": c["created_at"],
            "name": c.get("name", ""),
            "email": email,
            "total_spent": total_spent,
            "purchases_count": len(payments),
        })

    repeat_purchase_rate = round((repeat_count / total * 100), 1) if total > 0 else 0
    avg_clv = round((total_spent_all / total), 2) if total > 0 else 0

    return {
        "total": total,
        "repeat_purchase_rate": repeat_purchase_rate,
        "avg_clv": avg_clv,
        "customers": out,
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

