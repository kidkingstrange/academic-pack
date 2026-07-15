import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from ..database import get_db
from ..config import get_settings
from ..middleware.auth import require_sales_rep
from ..utils.security import verify_password, hash_password, create_access_token

router = APIRouter(prefix="/api/sales", tags=["sales"])
settings = get_settings()

# ─── Schemas ──────────────────────────────────────────────────────────────────
class SalesRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)

class SalesLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LeadCreateRequest(BaseModel):
    offer_id: str
    prospect_name: str = Field(..., min_length=2, max_length=100)
    prospect_email: EmailStr
    prospect_phone: str = Field(..., min_length=5, max_length=20)

class LeadInfoResponse(BaseModel):
    id: str
    prospect_name: str
    prospect_email: str
    prospect_phone: str
    offer_name: str
    offer_price: float
    checkout_url: str
    status: str
    created_at: datetime

# ─── Endpoints ────────────────────────────────────────────────────────────────
@router.post("/register")
async def register_sales_rep(body: SalesRegisterRequest, db=Depends(get_db)):
    existing = await db.sales_reps.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Sales representative already exists")

    rep = {
        "name": body.name,
        "email": body.email.lower(),
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(timezone.utc),
        "active": True
    }
    await db.sales_reps.insert_one(rep)
    return {"status": "ok", "message": "Sales representative registered successfully"}

@router.post("/login", response_model=TokenResponse)
async def sales_login(body: SalesLoginRequest, db=Depends(get_db)):
    rep = await db.sales_reps.find_one({"email": body.email.lower(), "active": True})
    if not rep or not verify_password(body.password, rep["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid sales credentials")

    token = create_access_token({"sub": str(rep["_id"]), "email": rep["email"], "role": "sales_rep"})
    return TokenResponse(access_token=token)

@router.get("/offers")
async def get_sales_offers(current_user=Depends(require_sales_rep), db=Depends(get_db)):
    offers = await db.offers.find({}).sort("name", 1).to_list(100)
    out = []
    for o in offers:
        out.append({
            "id": str(o["_id"]),
            "name": o["name"],
            "description": o["description"],
            "price": o["price"],
            "billing_type": o["billing_type"],
            "duration_months": o.get("duration_months")
        })
    return {"offers": out}

@router.post("/leads")
async def create_sales_lead(
    body: LeadCreateRequest,
    current_user=Depends(require_sales_rep),
    db=Depends(get_db)
):
    try:
        offer_oid = ObjectId(body.offer_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid offer ID format")

    offer = await db.offers.find_one({"_id": offer_oid})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    token = secrets.token_urlsafe(24)
    lead = {
        "sales_rep_id": ObjectId(current_user["user_id"]),
        "offer_id": offer_oid,
        "prospect_name": body.prospect_name,
        "prospect_email": body.prospect_email.lower(),
        "prospect_phone": body.prospect_phone,
        "generated_link_token": token,
        "status": "link_generated",
        "created_at": datetime.now(timezone.utc),
    }
    await db.sales_leads.insert_one(lead)

    checkout_url = f"{settings.APP_URL}/sales/checkout?token={token}"
    return {
        "status": "ok",
        "checkout_url": checkout_url,
        "lead_token": token
    }

@router.get("/leads", response_model=List[LeadInfoResponse])
async def get_sales_leads(current_user=Depends(require_sales_rep), db=Depends(get_db)):
    rep_oid = ObjectId(current_user["user_id"])
    leads = await db.sales_leads.find({"sales_rep_id": rep_oid}).sort("created_at", -1).to_list(200)

    # Resolve offers
    offer_ids = list({l["offer_id"] for l in leads})
    offers_list = await db.offers.find({"_id": {"$in": offer_ids}}).to_list(len(offer_ids))
    offers_map = {o["_id"]: o for o in offers_list}

    out = []
    for l in leads:
        offer = offers_map.get(l["offer_id"], {})
        out.append(LeadInfoResponse(
            id=str(l["_id"]),
            prospect_name=l["prospect_name"],
            prospect_email=l["prospect_email"],
            prospect_phone=l["prospect_phone"],
            offer_name=offer.get("name", "Unknown Offer"),
            offer_price=offer.get("price", 0.0),
            checkout_url=f"{settings.APP_URL}/sales/checkout?token={l['generated_link_token']}",
            status=l["status"],
            created_at=l["created_at"]
        ))
    return out

@router.get("/me")
async def get_me(current_user=Depends(require_sales_rep), db=Depends(get_db)):
    rep_oid = ObjectId(current_user["user_id"])
    rep = await db.sales_reps.find_one({"_id": rep_oid})
    if not rep:
        raise HTTPException(status_code=404, detail="Representative not found")
    return {
        "id": str(rep["_id"]),
        "name": rep["name"],
        "email": rep["email"]
    }
