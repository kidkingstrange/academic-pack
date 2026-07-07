"""
Payment routes — Flutterwave V4 bank transfer flow.
"""
import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from ..schemas.schemas import (
    PaymentInitRequest, PaymentInitResponse,
    PaymentVerifyRequest, PaymentVerifyResponse,
)
from ..services.flutterwave import (
    get_flw_token, create_flw_customer,
    initiate_bank_transfer, verify_flw_charge,
    create_virtual_account, verify_charges_by_reference,
)
from ..services.payment_completion import complete_payment
from ..utils.security import create_access_token
from ..database import get_db
from ..config import get_settings

router = APIRouter(prefix="/api/payments", tags=["payments"])
settings = get_settings()


@router.post("/initialize", response_model=PaymentInitResponse)
async def init_payment(body: PaymentInitRequest, request: Request, db=Depends(get_db)):
    """
    Step 1: Determine price, create Flutterwave customer,
    initiate bank-transfer charge, return virtual account details.
    """
    reference = f"ACP-{uuid.uuid4().hex[:12].upper()}"
    amount_naira = settings.PRODUCT_PRICE_NAIRA
    now = datetime.now(timezone.utc)

    # ── Server-side 24-hour price check ──────────────────────────────
    existing_lead = await db.leads.find_one({"email": body.email.lower()})
    is_expired = False
    if existing_lead:
        created_at = existing_lead.get("created_at")
        if created_at:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if (now - created_at).total_seconds() > 24 * 3600:
                is_expired = True
    else:
        if body.client_expiry:
            if body.client_expiry < now.timestamp() * 1000:
                is_expired = True

    if is_expired:
        amount_naira = settings.PRODUCT_PRICE_LATE_NAIRA

    # ── Upsert lead ───────────────────────────────────────────────────
    await db.leads.update_one(
        {"email": body.email.lower()},
        {
            "$set": {
                "name": body.name,
                "email": body.email.lower(),
                "source": "landing_page",
                "ip_address": request.client.host,
                "converted": False,
                "price_offered": amount_naira,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    # ── Flutterwave: get token → customer ────────────────────────────────
    try:
        token       = await get_flw_token()
        customer_id = await create_flw_customer(token, body.name, body.email.lower())
    except Exception as e:
        print(f"❌ FLW initiation error: {e}")
        raise HTTPException(status_code=502, detail="Payment gateway error. Please try again.")

    payment_method = (body.payment_method or "pay_with_bank").strip().lower()

    if payment_method == "bank_transfer":
        # ── Virtual Account path ──────────────────────────────────────
        try:
            narration = f"{body.name} - Academic Comeback Package"
            va_data = await create_virtual_account(
                token, customer_id, amount_naira, reference, narration
            )
        except Exception as e:
            print(f"❌ FLW virtual-account error: {e}")
            raise HTTPException(status_code=502, detail="Payment gateway error. Please try again.")

        va_id = va_data.get("id")
        await db.pending_payments.update_one(
            {"reference": reference},
            {"$set": {
                "reference":      reference,
                "va_id":          va_id,
                "charge_id":      None,
                "payment_method": "bank_transfer",
                "email":          body.email.lower(),
                "name":           body.name,
                "amount":         amount_naira,
                "customer_id":    customer_id,
                "created_at":     now,
            }},
            upsert=True,
        )

        return PaymentInitResponse(
            reference=reference,
            va_id=va_id,
            action="virtual_account",
            account_number=va_data.get("account_number", ""),
            bank_name=va_data.get("account_bank_name", ""),
            amount=amount_naira,
            amount_with_fee=int(va_data.get("amount", amount_naira)),
            expiry=va_data.get("account_expiration_datetime"),
            note=va_data.get("note", "Transfer the exact amount shown. Account is valid for 60 minutes."),
        )

    # ── Pay with Bank path (existing behavior) ────────────────────────
    try:
        redirect_url = f"{settings.APP_URL}/api/payments/callback"
        charge      = await initiate_bank_transfer(
            token, customer_id, amount_naira, reference, redirect_url
        )
    except Exception as e:
        print(f"❌ FLW initiation error: {e}")
        raise HTTPException(status_code=502, detail="Payment gateway error. Please try again.")

    # ── Save pending order ────────────────────────────────────────────
    charge_id = charge.get("id")
    await db.pending_payments.update_one(
        {"reference": reference},
        {"$set": {
            "reference":      reference,
            "charge_id":      charge_id,
            "va_id":          None,
            "payment_method": "pay_with_bank",
            "email":          body.email.lower(),
            "name":           body.name,
            "amount":         amount_naira,
            "customer_id":    customer_id,
            "created_at":     now,
        }},
        upsert=True,
    )

    # ── Determine action and return ───────────────────────────────────
    next_action = charge.get("next_action", {})
    action_type = next_action.get("type")

    if action_type == "redirect_url":
        return PaymentInitResponse(
            reference=reference,
            charge_id=charge_id,
            action="redirect",
            redirect_url=next_action["redirect_url"]["url"],
            amount=amount_naira,
        )

    # Default: bank_transfer (from charge)
    va = charge.get("payment_method_details", {}).get("bank_transfer", {})
    instruction = next_action.get("payment_instruction", {})
    return PaymentInitResponse(
        reference=reference,
        charge_id=charge_id,
        action="bank_transfer",
        account_number=va.get("account_number", ""),
        bank_name=va.get("bank_name", ""),
        amount=amount_naira,
        note=instruction.get("note", "Transfer the exact amount. Account is valid for 30 minutes."),
    )


@router.post("/verify", response_model=PaymentVerifyResponse)
async def verify_payment(body: PaymentVerifyRequest, request: Request, db=Depends(get_db)):
    """
    Step 2: Frontend polls this after customer claims to have paid.
    Verifies charge with Flutterwave, then runs complete_payment() —
    the same shared completion path used by the webhook and /callback.
    """
    # Fast path: already confirmed. Avoid re-hitting Flutterwave, but still
    # self-heal via complete_payment() if the subscriber/email queue never
    # got created (e.g. the webhook claimed the payment but died before
    # reaching that step) — this is the exact gap that used to grant
    # access without ever enrolling the customer.
    existing_payment = await db.payments.find_one({"reference": body.reference, "status": "success"})
    if existing_payment:
        existing_sub = await db.subscribers.find_one({"email": body.email.lower()})
        if existing_sub:
            user = await db.users.find_one({"email": body.email.lower()})
            if user:
                token = create_access_token({"sub": str(user["_id"]), "email": user["email"], "role": "customer"})
                return PaymentVerifyResponse(success=True, token=token)
        completion = await complete_payment(
            db,
            reference=body.reference,
            email=body.email,
            name=body.name,
            amount=existing_payment.get("amount", 0),
            charge_id=existing_payment.get("charge_id"),
            gateway_response=existing_payment.get("gateway_response", {}),
            ip_address=request.client.host,
        )
        return PaymentVerifyResponse(success=True, token=completion["token"])

    # Verify with Flutterwave — branch on payment method
    payment_method = (body.payment_method or "pay_with_bank").strip().lower()

    if payment_method == "bank_transfer":
        # ── Virtual Account verification path ─────────────────────────
        try:
            result = await verify_charges_by_reference(body.reference)
        except Exception as e:
            print(f"❌ FLW VA verify error: {e}")
            return PaymentVerifyResponse(success=False, message="Could not verify payment. Please try again.")

        if result.get("status") != "success":
            return PaymentVerifyResponse(success=False, message="Payment not yet confirmed. Please wait and try again.")

        charges = result.get("data", [])
        if not isinstance(charges, list):
            charges = [charges] if charges else []

        succeeded_charge = None
        for chg in charges:
            if chg.get("status") == "succeeded":
                succeeded_charge = chg
                break

        if not succeeded_charge:
            return PaymentVerifyResponse(
                success=False,
                message="Payment not yet confirmed. Please complete the transfer and try again."
            )

        amount_paid = int(succeeded_charge.get("amount", 0))
        # Keep gateway response reference matching expected shape
        charge = succeeded_charge
    else:
        # ── Charge verification path (existing) ──────────────────────
        try:
            result = await verify_flw_charge(body.charge_id)
        except Exception as e:
            print(f"❌ FLW verify error: {e}")
            return PaymentVerifyResponse(success=False, message="Could not verify payment. Please try again.")

        if result.get("status") != "success":
            return PaymentVerifyResponse(success=False, message="Payment not yet confirmed. Please wait and try again.")

        charge = result["data"]
        charge_status = charge.get("status")

        if charge_status != "succeeded":
            return PaymentVerifyResponse(
                success=False,
                message=f"Payment status: {charge_status}. Please complete the transfer and try again."
            )

        amount_paid = charge.get("amount", 0)

    now = datetime.now(timezone.utc)

    # ── 24-hour price enforcement ─────────────────────────────────────
    lead = await db.leads.find_one({"email": body.email.lower()})
    if lead:
        created_at = lead.get("created_at")
        if created_at:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if (now - created_at).total_seconds() > 24 * 3600:
                if amount_paid < settings.PRODUCT_PRICE_LATE_NAIRA:
                    await db.payments.update_one(
                        {"reference": body.reference},
                        {"$set": {
                            "reference": body.reference,
                            "email": body.email.lower(),
                            "status": "failed",
                            "created_at": now,
                            "failure_reason": "Promo expired — paid ₦2,000 instead of ₦5,000",
                        }},
                        upsert=True,
                    )
                    return PaymentVerifyResponse(
                        success=False,
                        message="The 24-hour promotional price has expired. Standard price of ₦5,000 applies.",
                    )

    completion = await complete_payment(
        db,
        reference=body.reference,
        email=body.email,
        name=body.name,
        amount=amount_paid,
        charge_id=body.charge_id,
        gateway_response=charge,
        ip_address=request.client.host,
    )

    return PaymentVerifyResponse(success=True, token=completion["token"])


@router.get("/callback")
async def payment_callback(
    request: Request,
    status: str = "",
    tx_ref: str = "",
    reference: str = "",
    db=Depends(get_db),
):
    """
    Flutterwave redirects here after 3DS/redirect payments.
    Looks up the pending order and redirects to welcome page with token.
    """
    from fastapi.responses import RedirectResponse

    ref = tx_ref or reference
    if not ref:
        return RedirectResponse("/?error=missing_reference")

    pending = await db.pending_payments.find_one({"reference": ref})
    if not pending:
        return RedirectResponse("/?error=order_not_found")

    charge_id = pending.get("charge_id")
    if not charge_id:
        return RedirectResponse("/?error=charge_not_found")

    try:
        result = await verify_flw_charge(charge_id)
        charge = result.get("data", {})
    except Exception:
        return RedirectResponse("/?error=verify_failed")

    if charge.get("status") != "succeeded":
        return RedirectResponse("/?error=payment_not_confirmed")

    email = pending["email"]
    name  = pending["name"]
    now   = datetime.now(timezone.utc)

    completion = await complete_payment(
        db,
        reference=ref,
        email=email,
        name=name,
        amount=charge.get("amount", 0),
        charge_id=charge_id,
        gateway_response=charge,
        ip_address=request.client.host,
    )

    # Separate, short-lived magic link purely for this immediate browser
    # handoff — distinct from the one emailed in the welcome message.
    redirect_magic_token = secrets.token_urlsafe(32)
    await db.magic_links.insert_one({
        "token": redirect_magic_token,
        "user_id": completion["user_id"],
        "purpose": "welcome",
        "expires_at": now + timedelta(days=90),
        "used": False,
        "created_at": now,
    })

    return RedirectResponse(f"/api/auth/magic?token={redirect_magic_token}&redirect=/welcome")


# ── Webhook processing helper ───────────────────────────────────────────────
async def process_webhook_payment(payload: dict, db):
    data = payload.get("data", {})
    ref = data.get("tx_ref")
    if not ref:
        print("⚠️ Webhook payload missing tx_ref")
        return

    # Find pending payment
    pending = await db.pending_payments.find_one({"reference": ref})
    if not pending:
        # Check if it starts with our prefix to avoid processing random webhooks
        if not str(ref).startswith("ACP-"):
            print(f"⚠️ Webhook: Unknown non-ACP reference {ref}")
            return
        email = data.get("customer", {}).get("email")
        name = data.get("customer", {}).get("name") or "Valued Customer"
        amount_paid = float(data.get("amount", 2000))
        charge_id = str(data.get("id"))
    else:
        email = pending.get("email")
        name = pending.get("name")
        amount_paid = pending.get("amount", 2000)
        charge_id = pending.get("charge_id") or pending.get("va_id") or str(data.get("id"))

    if not email:
        print(f"⚠️ Webhook: Missing customer email for {ref}")
        return

    # complete_payment() is idempotent — if this reference was already
    # claimed (e.g. by the frontend poll), this call still checks and
    # backfills a missing subscriber/email-queue instead of silently
    # returning early like the old pre-check here used to.
    await complete_payment(
        db,
        reference=ref,
        email=email,
        name=name,
        amount=amount_paid,
        charge_id=charge_id,
        gateway_response=data,
    )
    print(f"✅ Webhook: Payment {ref} processed (completion verified/backfilled).")


# ── Webhook endpoint ──────────────────────────────────────────────────────────
@router.post("/webhook")
async def flutterwave_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    Asynchronous webhook endpoint for Flutterwave payment completion events.
    Verifies the flutterwave-signature header (HMAC-SHA256 of the raw body,
    keyed with FLW_WEBHOOK_SECRET_HASH) before processing.
    """
    raw_body = await request.body()

    # 1. Signature Verification
    if settings.FLW_WEBHOOK_SECRET_HASH:
        received_signature = request.headers.get("flutterwave-signature")
        expected_signature = base64.b64encode(
            hmac.new(
                settings.FLW_WEBHOOK_SECRET_HASH.encode(),
                raw_body,
                hashlib.sha256,
            ).digest()
        ).decode()
        if not received_signature or not hmac.compare_digest(received_signature, expected_signature):
            print("❌ Webhook unauthorized: Invalid or missing flutterwave-signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # 2. Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event")
    data = payload.get("data", {})
    status = data.get("status")

    print(f"📥 Received Flutterwave webhook: event={event}, status={status}")

    # 3. Handle successful charge events
    if event == "charge.completed" and status == "successful":
        background_tasks.add_task(process_webhook_payment, payload, db)

    # Always return 200 OK immediately to acknowledge receipt
    return {"status": "received"}
