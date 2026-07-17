import html
import httpx
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from ..database import get_db
from ..config import get_settings
from ..middleware.auth import require_sales_rep, require_admin
from ..utils.security import verify_password, hash_password, create_access_token
from ..utils.rate_limit import limiter
from ..services.flutterwave import (
    create_flw_customer, get_flw_token, initiate_card_payment, verify_flw_charge, FLW_API_BASE
)
from ..services.email_service import send_email

router = APIRouter(prefix="/api/sales", tags=["sales"])
settings = get_settings()

# ─── Schemas ──────────────────────────────────────────────────────────────────
class SalesRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)

from ..schemas.schemas import TokenResponse

class SalesLoginRequest(BaseModel):
    email: EmailStr
    password: str

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

class CancelRequest(BaseModel):
    email: EmailStr

class CancelConfirmRequest(BaseModel):
    token: str

# ─── Endpoints ────────────────────────────────────────────────────────────────
@router.post("/register")
@limiter.limit("5/hour")
async def register_sales_rep(request: Request, body: SalesRegisterRequest, db=Depends(get_db)):
    """Self-registration via the link an admin shares (see
    copySelfRegistrationLink() in the admin dashboard). The account is
    created inactive — it shows up in the admin's Team Members list exactly
    like any other suspended rep, and only gets a working login once an
    admin explicitly clicks Activate there. Previously this created a
    fully active, immediately-usable account with no approval step at all."""
    existing = await db.sales_reps.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Sales representative already exists")

    rep = {
        "name": body.name,
        "email": body.email.lower(),
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(timezone.utc),
        "active": False,
    }
    await db.sales_reps.insert_one(rep)
    try:
        await send_email(
            settings.ADMIN_EMAIL,
            "New sales rep self-registration pending approval",
            f"<p><b>{body.name}</b> ({body.email}) just self-registered as a sales rep "
            f"and is awaiting approval.</p>"
            f"<p>Review and activate them from the Team Members tab in the admin dashboard.</p>",
        )
    except Exception as alert_err:
        print(f"❌ Failed to send sales-rep pending-approval alert: {alert_err}")
    return {
        "status": "ok",
        "message": "Registration received. An admin will review and activate your account before you can log in.",
    }

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def sales_login(request: Request, body: SalesLoginRequest, db=Depends(get_db)):
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

    if body.payment_method_id == "mock-payment-method-id" and settings.APP_ENV == "development":
        # Bypass FLW call for simulation / sandbox card testing — only ever
        # allowed in local development. Gated by an explicit allow-list
        # check (APP_ENV == "development") rather than != "production" so a
        # misconfigured/unset APP_ENV can't accidentally enable it.
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

    try:
        customer_id = await create_flw_customer(
            flw_token,
            lead.get("prospect_name") or lead["prospect_email"],
            lead["prospect_email"].lower()
        )
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
                    "customer_id":       customer_id,
                    "payment_method_id": body.payment_method_id,
                    "redirect_url":      redirect_url,
                },
                timeout=15,
            )
            chg_data = chg_resp.json()
            if chg_data.get("status") != "success":
                msg = chg_data.get("message") or "Payment gateway charge failed"
                raise HTTPException(status_code=502, detail=f"Card payment failed: {msg}")
            charge = chg_data["data"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Card payment gateway error: {str(e)}")

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

    if pending["charge_id"].startswith("MOCK-") and settings.APP_ENV == "development":
        # Simulated success path — defense in depth: even if a MOCK- record
        # somehow exists (e.g. a leftover from before this env gate), it can
        # still only simulate success in development.
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


# ─── Cancellation Endpoints ──────────────────────────────────────────────────
@router.post("/subscriptions/request-cancel")
async def request_subscription_cancel(body: CancelRequest, db=Depends(get_db)):
    sub = await db.subscriptions.find_one({
        "customer_email": body.email.lower(),
        "status": {"$in": ["active", "past_due"]}
    })
    if not sub:
        raise HTTPException(
            status_code=404,
            detail="No active or past-due subscription found for this email address"
        )

    offer = await db.offers.find_one({"_id": sub["offer_id"]})
    offer_name = offer["name"] if offer else "Your Subscription"

    cancel_token = secrets.token_urlsafe(24)
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)

    await db.subscriptions.update_one(
        {"_id": sub["_id"]},
        {"$set": {
            "cancellation_token": cancel_token,
            "cancellation_token_expiry": expiry
        }}
    )

    cancel_link = f"{settings.APP_URL}/sales/cancel?token={cancel_token}"

    email_html = f"""
    <h2>Subscription Cancellation Request</h2>
    <p>Hello {html.escape(sub['customer_name'])},</p>
    <p>We received a request to cancel your subscription for <strong>{html.escape(offer_name)}</strong>.</p>
    <p>To confirm and complete your cancellation, please click the secure link below (valid for 1 hour):</p>
    <p><a href="{cancel_link}" style="display:inline-block;background-color:#dc2626;color:#ffffff;padding:12px 24px;border-radius:30px;text-decoration:none;font-weight:bold">Confirm Subscription Cancellation &rarr;</a></p>
    <br>
    <p><em>If you did not request this, you can safely ignore this email. Your subscription remains active.</em></p>
    """
    await send_email(sub["customer_email"], "Cancel Your Subscription Request", email_html)
    return {"status": "ok", "message": "Cancellation confirmation email sent"}


@router.get("/subscriptions/cancel-info")
async def get_cancel_info(token: str, db=Depends(get_db)):
    now = datetime.now(timezone.utc)
    sub = await db.subscriptions.find_one({
        "cancellation_token": token,
        "cancellation_token_expiry": {"$gt": now}
    })
    if not sub:
        raise HTTPException(
            status_code=400,
            detail="Cancellation link is invalid or has expired. Please request a new link."
        )

    offer = await db.offers.find_one({"_id": sub["offer_id"]})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer details not found")

    return {
        "customer_name": sub["customer_name"],
        "customer_email": sub["customer_email"],
        "offer_name": offer["name"],
        "offer_price": offer["price"],
        "status": sub["status"]
    }


@router.post("/subscriptions/cancel-confirm")
async def confirm_subscription_cancel(body: CancelConfirmRequest, db=Depends(get_db)):
    now = datetime.now(timezone.utc)
    sub = await db.subscriptions.find_one({
        "cancellation_token": body.token,
        "cancellation_token_expiry": {"$gt": now}
    })
    if not sub:
        raise HTTPException(
            status_code=400,
            detail="Cancellation link is invalid or has expired. Please request a new link."
        )

    offer = await db.offers.find_one({"_id": sub["offer_id"]})
    offer_name = offer["name"] if offer else "Your Subscription"

    # Update subscription status to cancelled and clear cancellation token
    await db.subscriptions.update_one(
        {"_id": sub["_id"]},
        {
            "$set": {
                "status": "cancelled",
                "cancelled_at": now,
                "updated_at": now
            },
            "$unset": {
                "cancellation_token": "",
                "cancellation_token_expiry": ""
            }
        }
    )

    email_html = f"""
    <h2>Subscription Cancelled</h2>
    <p>Hello {html.escape(sub['customer_name'])},</p>
    <p>Your subscription for <strong>{html.escape(offer_name)}</strong> has been cancelled successfully as requested.</p>
    <p>You will not be billed again. Thank you for your time with us!</p>
    """
    await send_email(sub["customer_email"], f"Subscription Cancelled: {offer_name}", email_html)
    return {"status": "ok", "message": "Subscription cancelled successfully"}


@router.post("/subscriptions/{subscription_id}/admin-cancel")
async def admin_cancel_subscription(subscription_id: str, current_user=Depends(require_admin), db=Depends(get_db)):
    try:
        sub_oid = ObjectId(subscription_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid subscription ID format")

    sub = await db.subscriptions.find_one({"_id": sub_oid})
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if sub["status"] == "cancelled":
        return {"status": "ok", "message": "Subscription is already cancelled"}

    offer = await db.offers.find_one({"_id": sub["offer_id"]})
    offer_name = offer["name"] if offer else "Your Subscription"

    now = datetime.now(timezone.utc)
    await db.subscriptions.update_one(
        {"_id": sub_oid},
        {"$set": {
            "status": "cancelled",
            "cancelled_at": now,
            "updated_at": now,
            "cancelled_by": "admin"
        }}
    )

    email_html = f"""
    <h2>Subscription Cancelled by Administrator</h2>
    <p>Hello {html.escape(sub['customer_name'])},</p>
    <p>An administrator has cancelled your active subscription for <strong>{html.escape(offer_name)}</strong>.</p>
    <p>No further charges will be made. If you have questions, please contact support.</p>
    """
    await send_email(sub["customer_email"], f"Subscription Cancelled: {offer_name}", email_html)
    return {"status": "ok", "message": "Subscription successfully cancelled by administrator"}
