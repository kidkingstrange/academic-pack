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
    page: int = 1, limit: int = 20,
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
