import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from ..database import get_db
from ..config import get_settings
from ..middleware.auth import require_sales_rep
from ..utils.security import verify_password, hash_password, create_access_token
from ..services.flutterwave import (
    create_flw_customer, get_flw_token, initiate_card_payment, verify_flw_charge
)

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

class CheckoutPayRequest(BaseModel):
    token: str
    payment_method_id: str

class CheckoutVerifyRequest(BaseModel):
    reference: str

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


# ─── Checkout Public Endpoints ───────────────────────────────────────────────
@router.get("/checkout/info")
async def get_checkout_info(token: str, db=Depends(get_db)):
    lead = await db.sales_leads.find_one({"generated_link_token": token})
    if not lead:
        raise HTTPException(status_code=404, detail="Invalid checkout link")

    offer = await db.offers.find_one({"_id": lead["offer_id"]})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    return {
        "prospect_name": lead["prospect_name"],
        "prospect_email": lead["prospect_email"],
        "prospect_phone": lead["prospect_phone"],
        "offer_name": offer["name"],
        "offer_description": offer["description"],
        "offer_price": offer["price"],
        "offer_billing_type": offer["billing_type"]
    }

@router.post("/checkout/pay")
async def process_checkout_payment(body: CheckoutPayRequest, db=Depends(get_db)):
    import httpx
    import uuid
    lead = await db.sales_leads.find_one({"generated_link_token": body.token})
    if not lead:
        raise HTTPException(status_code=404, detail="Invalid checkout link")

    if lead["status"] == "paid":
        raise HTTPException(status_code=400, detail="This invoice has already been paid")

    offer = await db.offers.find_one({"_id": lead["offer_id"]})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    reference = f"SUB-{secrets.token_hex(8).upper()}"

    if body.payment_method_id == "mock-payment-method-id":
        # Bypass FLW call for simulation / sandbox card testing
        charge_id = f"MOCK-{secrets.token_hex(12).upper()}"
        await db.pending_subscription_payments.insert_one({
            "reference": reference,
            "charge_id": charge_id,
            "lead_token": body.token,
            "status": "pending",
            "created_at": datetime.now(timezone.utc)
        })
        return {
            "status": "success",
            "action": "none",
            "reference": reference
        }

    flw_token = await get_flw_token()
    redirect_url = f"{settings.APP_URL}/sales/checkout?reference={reference}"

    async with httpx.AsyncClient() as client:
        # Create charge using payment_method_id from client
        chg_resp = await client.post(
            f"{FLW_API_BASE}/charges",
            headers={
                "Authorization":     f"Bearer {flw_token}",
                "Content-Type":      "application/json",
                "X-Trace-Id":        str(uuid.uuid4()),
                "X-Idempotency-Key": reference,
            },
            json={
                "reference":         reference,
                "currency":          "NGN",
                "amount":            offer["price"],
                "customer_id":       lead["prospect_email"],
                "payment_method_id": body.payment_method_id,
                "redirect_url":      redirect_url,
            },
            timeout=15,
        )
        chg_data = chg_resp.json()
        if chg_data.get("status") != "success":
            raise Exception(f"FLW card charge error: {chg_data}")
        charge = chg_data["data"]

    charge_id = charge.get("id")

    # Store pending subscription payment record
    await db.pending_subscription_payments.insert_one({
        "reference": reference,
        "charge_id": charge_id,
        "lead_token": body.token,
        "status": "pending",
        "created_at": datetime.now(timezone.utc)
    })

    # Return action
    next_action = charge.get("next_action", {})
    action_type = next_action.get("type")
    
    if action_type == "redirect_url":
        return {
            "status": "pending",
            "action": "redirect",
            "redirect_url": next_action["redirect_url"]["url"],
            "reference": reference
        }
    
    return {
        "status": "success",
        "action": "none",
        "reference": reference
    }

@router.post("/checkout/verify")
async def verify_checkout_payment(body: CheckoutVerifyRequest, db=Depends(get_db)):
    pending = await db.pending_subscription_payments.find_one({"reference": body.reference})
    if not pending:
        raise HTTPException(status_code=404, detail="Payment record not found")

    if pending["status"] == "success":
        return {"success": True, "message": "Payment verified successfully"}

    if pending["charge_id"].startswith("MOCK-"):
        # Simulated success path
        charge_resp = {
            "status": "success",
            "data": {
                "status": "succeeded",
                "card": {
                    "token": "mock-card-token-12345",
                    "last_4digits": "1111",
                    "brand": "Visa"
                }
            }
        }
    else:
        try:
            charge_resp = await verify_flw_charge(pending["charge_id"])
        except Exception as e:
            print(f"❌ FLW verify charge error: {e}")
            raise HTTPException(status_code=502, detail="Gateway error verifying payment")

    flw_status = charge_resp.get("status")
    charge_data = charge_resp.get("data", {})
    charge_status = charge_data.get("status")

    if flw_status != "success" or charge_status != "succeeded":
        # Check failed status
        if charge_status in ["failed", "declined"]:
            await db.pending_subscription_payments.update_one(
                {"reference": body.reference},
                {"$set": {"status": "failed", "gateway_response": charge_resp}}
            )
            # Update lead as abandoned
            await db.sales_leads.update_one(
                {"generated_link_token": pending["lead_token"]},
                {"$set": {"status": "abandoned"}}
            )
            return {"success": False, "message": "Card payment was declined or failed"}

        return {"success": False, "message": "Payment is still pending verification"}

    # Success! Extract card token and details
    pm = charge_data.get("payment_method", {})
    if pm.get("type") == "card":
        card_token = pm.get("card", {}).get("token")
        card_last4 = pm.get("card", {}).get("last_4digits", "")
        card_brand = pm.get("card", {}).get("brand", "")
    else:
        card_token = charge_data.get("card", {}).get("token")
        card_last4 = charge_data.get("card", {}).get("last_4digits", "")
        card_brand = charge_data.get("card", {}).get("brand", "")

    # Retrieve lead details
    lead = await db.sales_leads.find_one({"generated_link_token": pending["lead_token"]})
    if not lead:
        raise HTTPException(status_code=404, detail="Associated lead not found")

    offer = await db.offers.find_one({"_id": lead["offer_id"]})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    now = datetime.now(timezone.utc)

    # 1. Update pending payment
    await db.pending_subscription_payments.update_one(
        {"reference": body.reference},
        {"$set": {"status": "success", "gateway_response": charge_resp}}
    )

    # 2. Update Lead status to paid
    await db.sales_leads.update_one(
        {"_id": lead["_id"]},
        {"$set": {"status": "paid"}}
    )

    # 3. Create Subscription or One-Time Purchase record
    if offer["billing_type"] == "recurring_monthly":
        # Create active subscription
        sub = {
            "customer_name": lead["prospect_name"],
            "customer_email": lead["prospect_email"],
            "customer_phone": lead["prospect_phone"],
            "offer_id": lead["offer_id"],
            "sales_rep_id": lead["sales_rep_id"],
            "card_token": card_token,
            "card_last4": card_last4,
            "card_brand": card_brand,
            "status": "active",
            "next_charge_date": now + timedelta(days=30),
            "created_at": now
        }
        await db.subscriptions.insert_one(sub)
    else:
        # Create one-time purchase
        purchase = {
            "customer_name": lead["prospect_name"],
            "customer_email": lead["prospect_email"],
            "customer_phone": lead["prospect_phone"],
            "offer_id": lead["offer_id"],
            "sales_rep_id": lead["sales_rep_id"],
            "amount": offer["price"],
            "reference": body.reference,
            "created_at": now
        }
        await db.one_time_purchases.insert_one(purchase)

    return {"success": True, "message": "Payment processed and subscription activated successfully"}
