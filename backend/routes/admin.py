"""
Admin routes — login, customers, payments, analytics, product upload.
All routes require admin JWT.
"""
import os, shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from bson import ObjectId
from ..middleware.auth import require_admin
from ..utils.security import verify_password, hash_password, create_access_token
from ..database import get_db
from ..config import get_settings
from ..schemas.schemas import AdminLoginRequest, TokenResponse

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
    email = payment.get("email", "").lower()

    # Customer Profile Info
    customer = await db.users.find_one({"email": email}, {"password_hash": 0})
    if customer:
        customer["id"] = str(customer.pop("_id"))

    # Referral Attribution
    referral = await db.referrals.find_one({"reference": reference})
    if referral:
        referral["id"] = str(referral.pop("_id"))

    # Email Queue Delivery History
    emails = await db.email_queue.find({"recipient": email}).sort("scheduled_at", -1).to_list(20)
    for e in emails:
        e["id"] = str(e.pop("_id"))
        e["subscriber_id"] = str(e.get("subscriber_id", ""))

    # Downloads Activity History
    downloads = await db.downloads.find({"email": email}).sort("downloaded_at", -1).to_list(50)
    for d in downloads:
        d["id"] = str(d.pop("_id"))

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
    token = user.get("library_access_token") if user else "LIBRARY_TOKEN"

    # Queue a high-priority welcome email entry in email_queue
    sub = await db.subscribers.find_one({"email": email})
    sub_id = sub["_id"] if sub else None

    welcome_item = {
        "kind": "welcome",
        "subscriber_id": sub_id,
        "recipient": email,
        "email": email,
        "name": name,
        "access_token": token,
        "subject": "Access Granted: The Complete Academic Comeback Package 🎓",
        "template": "welcome.html",
        "scheduled_at": datetime.now(timezone.utc),
        "status": "pending",
        "retry_count": 0,
        "sent_at": None,
        "error": None,
    }
    await db.email_queue.insert_one(welcome_item)

    # Fire processing pass in background
    from ..workers.email_scheduler import trigger_email_queue_processing
    trigger_email_queue_processing()

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

    customer["id"] = str(customer.pop("_id"))

    # Purchases & Payments History
    payments = await db.payments.find({"email": email_clean}).sort("verified_at", -1).to_list(100)
    total_spent = 0
    for p in payments:
        p["id"] = str(p.pop("_id"))
        if p.get("status") == "success":
            total_spent += p.get("amount", 0)

    # Downloads Activity Log
    downloads = await db.downloads.find({"email": email_clean}).sort("downloaded_at", -1).to_list(100)
    for d in downloads:
        d["id"] = str(d.pop("_id"))

    # Email Delivery Logs
    emails = await db.email_queue.find({"recipient": email_clean}).sort("scheduled_at", -1).to_list(50)
    for e in emails:
        e["id"] = str(e.pop("_id"))

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

