"""
Pre-order routes — payment initialization, verification, customer refund requests,
and admin fulfillment tracking for multi-book home page.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends, Query
from pydantic import BaseModel, EmailStr

from ..database import get_db
from ..config import get_settings
from ..services.paystack import initialize_transaction, verify_transaction
from ..middleware.auth import require_admin
from ..utils.rate_limit import limiter, get_real_client_ip

router = APIRouter(prefix="/api", tags=["preorders"])
settings = get_settings()


class PreorderInitRequest(BaseModel):
    name: str
    email: EmailStr
    book_id: str
    book_title: str
    amount: float = 5000.0
    payment_method: str = "pay_with_bank"
    referral_code: Optional[str] = None


class PreorderVerifyRequest(BaseModel):
    reference: str
    email: EmailStr
    name: str
    book_id: str
    book_title: str


class RefundRequestPayload(BaseModel):
    reference: str
    email: EmailStr
    reason: str


@router.post("/payments/preorder/initialize")
@limiter.limit("10/minute")
async def init_preorder_payment(body: PreorderInitRequest, request: Request, db=Depends(get_db)):
    """Initialize a Paystack transaction for a ₦5,000 book pre-order."""
    reference = f"ACP-PRE-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.now(timezone.utc)
    email_clean = body.email.lower().strip()
    amount = float(body.amount) if body.amount > 0 else 5000.0

    payment_method = (body.payment_method or "pay_with_bank").strip().lower()
    channels = ["bank_transfer"] if payment_method == "bank_transfer" else (["card"] if payment_method == "card" else None)

    callback_url = f"{settings.APP_URL}/api/payments/preorder/callback"

    try:
        tx_data = await initialize_transaction(
            email=email_clean,
            amount_naira=amount,
            reference=reference,
            callback_url=callback_url,
            metadata={
                "type": "preorder",
                "name": body.name,
                "book_id": body.book_id,
                "book_title": body.book_title,
                "payment_method": payment_method,
            },
            channels=channels,
        )
    except Exception as e:
        print(f"❌ Paystack preorder initiation error: {e}")
        raise HTTPException(status_code=502, detail="Payment gateway error. Please try again.")

    redirect_url = tx_data.get("authorization_url")
    access_code = tx_data.get("access_code")

    await db.pending_payments.update_one(
        {"reference": reference},
        {"$set": {
            "reference": reference,
            "charge_id": access_code,
            "is_preorder": True,
            "book_id": body.book_id,
            "book_title": body.book_title,
            "payment_method": payment_method,
            "email": email_clean,
            "name": body.name,
            "amount": amount,
            "currency": "NGN",
            "created_at": now,
            "referred_by": body.referral_code,
        }},
        upsert=True,
    )

    return {
        "reference": reference,
        "charge_id": access_code,
        "action": "redirect",
        "redirect_url": redirect_url,
        "amount": amount,
    }


@router.post("/payments/preorder/verify")
@limiter.limit("30/minute")
async def verify_preorder_payment(body: PreorderVerifyRequest, request: Request, db=Depends(get_db)):
    """Verify Paystack pre-order payment and record in db.pre_orders."""
    email_clean = body.email.lower().strip()

    existing_preorder = await db.pre_orders.find_one({"reference": body.reference})
    if existing_preorder:
        return {
            "success": True,
            "message": "Pre-order already confirmed! You'll receive your book by email within 7 days.",
            "reference": body.reference,
            "book_title": existing_preorder.get("book_title"),
            "delivered": existing_preorder.get("delivered", False),
        }

    try:
        result = await verify_transaction(body.reference)
    except Exception as e:
        print(f"❌ Paystack preorder verify error: {e}")
        return {"success": False, "message": "Could not verify payment. Please try again."}

    if not result.get("status"):
        return {"success": False, "message": "Payment not yet confirmed. Please wait and try again."}

    data = result.get("data", {})
    if data.get("status") != "success":
        return {"success": False, "message": "Payment not yet confirmed. Please complete payment and try again."}

    amount_paid = data.get("amount", 0) / 100.0
    now = datetime.now(timezone.utc)

    pending = await db.pending_payments.find_one({"reference": body.reference})
    book_id = body.book_id or (pending.get("book_id") if pending else "unknown-book")
    book_title = body.book_title or (pending.get("book_title") if pending else "Pre-order Book")
    customer_name = body.name or (pending.get("name") if pending else "Customer")

    pre_order_doc = {
        "reference": body.reference,
        "charge_id": str(data.get("id")),
        "email": email_clean,
        "name": customer_name,
        "book_id": book_id,
        "book_title": book_title,
        "amount": amount_paid,
        "currency": "NGN",
        "paid_at": now,
        "created_at": now,
        "delivered": False,
        "delivered_at": None,
        "refund_requested": False,
        "refund_reason": None,
        "refund_requested_at": None,
        "gateway_response": data,
        "ip_address": get_real_client_ip(request),
    }

    await db.pre_orders.update_one(
        {"reference": body.reference},
        {"$set": pre_order_doc},
        upsert=True,
    )

    # Also log in main payments collection with type=preorder
    await db.payments.update_one(
        {"reference": body.reference},
        {"$set": {
            "reference": body.reference,
            "charge_id": str(data.get("id")),
            "email": email_clean,
            "name": customer_name,
            "amount": amount_paid,
            "currency": "NGN",
            "gateway": "paystack",
            "status": "success",
            "type": "preorder",
            "book_title": book_title,
            "created_at": now,
        }},
        upsert=True,
    )

    return {
        "success": True,
        "message": "Pre-order confirmed! You'll receive your book by email within 7 days.",
        "reference": body.reference,
        "book_title": book_title,
        "delivered": False,
    }


@router.get("/payments/preorder/callback")
async def preorder_callback(request: Request, trxref: str = "", reference: str = "", db=Depends(get_db)):
    """Paystack redirect handler for pre-orders."""
    from fastapi.responses import RedirectResponse
    ref = trxref or reference
    if not ref:
        return RedirectResponse("/?error=missing_reference")

    pending = await db.pending_payments.find_one({"reference": ref})
    book_title = pending.get("book_title", "Your Book") if pending else "Your Book"
    email = pending.get("email", "") if pending else ""
    name = pending.get("name", "") if pending else ""

    try:
        result = await verify_transaction(ref)
        data = result.get("data", {})
        if result.get("status") and data.get("status") == "success":
            now = datetime.now(timezone.utc)
            amount_paid = data.get("amount", 0) / 100.0
            pre_order_doc = {
                "reference": ref,
                "charge_id": str(data.get("id")),
                "email": email,
                "name": name,
                "book_id": pending.get("book_id", "book"),
                "book_title": book_title,
                "amount": amount_paid,
                "currency": "NGN",
                "paid_at": now,
                "created_at": now,
                "delivered": False,
                "delivered_at": None,
                "refund_requested": False,
                "refund_reason": None,
                "refund_requested_at": None,
                "gateway_response": data,
            }
            await db.pre_orders.update_one({"reference": ref}, {"$set": pre_order_doc}, upsert=True)
            return RedirectResponse(f"/?preorder_success=1&ref={ref}&title={book_title}")
    except Exception as e:
        print(f"❌ Preorder callback verification error: {e}")

    return RedirectResponse(f"/?preorder_success=1&ref={ref}")


@router.get("/preorders/status")
async def get_preorder_status(ref: str = Query("", description="Order Reference"), db=Depends(get_db)):
    """Customer lookup for pre-order status."""
    if not ref:
        raise HTTPException(status_code=400, detail="Missing reference")

    preorder = await db.pre_orders.find_one({"reference": ref})
    if not preorder:
        raise HTTPException(status_code=404, detail="Pre-order not found")

    now = datetime.now(timezone.utc)
    paid_at = preorder.get("paid_at") or preorder.get("created_at") or now
    if isinstance(paid_at, str):
        paid_at = datetime.fromisoformat(paid_at)
    if paid_at.tzinfo is None:
        paid_at = paid_at.replace(tzinfo=timezone.utc)

    days_since = (now - paid_at).days

    return {
        "reference": preorder.get("reference"),
        "email": preorder.get("email"),
        "name": preorder.get("name"),
        "book_title": preorder.get("book_title"),
        "amount": preorder.get("amount"),
        "paid_at": paid_at.isoformat(),
        "delivered": preorder.get("delivered", False),
        "delivered_at": preorder.get("delivered_at"),
        "days_since_purchase": days_since,
        "refund_requested": preorder.get("refund_requested", False),
        "refund_reason": preorder.get("refund_reason"),
    }


@router.post("/preorders/request-refund")
@limiter.limit("5/minute")
async def request_preorder_refund(body: RefundRequestPayload, request: Request, db=Depends(get_db)):
    """Customer refund request safety net."""
    email_clean = body.email.lower().strip()
    ref_clean = body.reference.strip()

    preorder = await db.pre_orders.find_one({"reference": ref_clean, "email": email_clean})
    if not preorder:
        raise HTTPException(status_code=404, detail="Matching pre-order not found for this email and reference.")

    if preorder.get("delivered"):
        raise HTTPException(status_code=400, detail="This order has already been delivered.")

    now = datetime.now(timezone.utc)
    await db.pre_orders.update_one(
        {"reference": ref_clean},
        {"$set": {
            "refund_requested": True,
            "refund_reason": body.reason.strip(),
            "refund_requested_at": now,
        }}
    )

    return {
        "success": True,
        "message": "Your refund request has been logged. Our support team will review and process your refund shortly.",
    }


# ── Admin Pre-Orders Endpoints (Phases 4 & 5) ──────────────────────────────
@router.get("/admin/preorders")
async def get_admin_preorders(
    admin=Depends(require_admin),
    db=Depends(get_db),
):
    """Fetch all pre-orders sorted by oldest undelivered first."""
    cursor = db.pre_orders.find({})
    preorders = await cursor.to_list(length=1000)

    now = datetime.now(timezone.utc)
    formatted = []
    for item in preorders:
        paid_at = item.get("paid_at") or item.get("created_at") or now
        if isinstance(paid_at, str):
            paid_at = datetime.fromisoformat(paid_at)
        if paid_at.tzinfo is None:
            paid_at = paid_at.replace(tzinfo=timezone.utc)

        days_since = (now - paid_at).days

        formatted.append({
            "id": str(item["_id"]),
            "reference": item.get("reference"),
            "charge_id": item.get("charge_id"),
            "email": item.get("email"),
            "name": item.get("name"),
            "book_id": item.get("book_id"),
            "book_title": item.get("book_title"),
            "amount": item.get("amount", 5000),
            "paid_at": paid_at.isoformat(),
            "days_since_purchase": days_since,
            "delivered": item.get("delivered", False),
            "delivered_at": item.get("delivered_at"),
            "refund_requested": item.get("refund_requested", False),
            "refund_reason": item.get("refund_reason"),
            "refund_requested_at": item.get("refund_requested_at"),
        })

    # Sorting: oldest undelivered first, then delivered
    formatted.sort(key=lambda x: (x["delivered"], x["paid_at"]))

    return {"pre_orders": formatted, "total_count": len(formatted)}


@router.post("/admin/preorders/{preorder_id}/deliver")
async def mark_preorder_delivered(
    preorder_id: str,
    admin=Depends(require_admin),
    db=Depends(get_db),
):
    """Manual 'mark as delivered' action for admin fulfillment."""
    from bson import ObjectId
    try:
        obj_id = ObjectId(preorder_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid pre-order ID")

    now = datetime.now(timezone.utc)
    res = await db.pre_orders.update_one(
        {"_id": obj_id},
        {"$set": {"delivered": True, "delivered_at": now}}
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pre-order not found")

    return {"success": True, "message": "Pre-order marked as delivered"}


@router.post("/admin/preorders/{preorder_id}/refund")
async def mark_preorder_refunded(
    preorder_id: str,
    admin=Depends(require_admin),
    db=Depends(get_db),
):
    """Mark refund as processed by admin."""
    from bson import ObjectId
    try:
        obj_id = ObjectId(preorder_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid pre-order ID")

    now = datetime.now(timezone.utc)
    res = await db.pre_orders.update_one(
        {"_id": obj_id},
        {"$set": {"refund_status": "processed", "refund_processed_at": now}}
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pre-order not found")

    return {"success": True, "message": "Pre-order refund marked as processed"}
