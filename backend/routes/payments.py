"""
Payment routes — Paystack payment flow.
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
from ..services.paystack import (
    initialize_transaction, verify_transaction
)
from ..services.payment_completion import complete_payment
from ..services.email_service import send_email
from ..utils.security import create_access_token
from ..database import get_db
from ..config import get_settings
from ..utils.rate_limit import limiter, get_real_client_ip

router = APIRouter(prefix="/api/payments", tags=["payments"])
settings = get_settings()


async def compute_price_and_referral(db, email: str, client_expiry: float = None, referral_code: str = None, currency: str = "NGN"):
    is_usd = (currency or "").strip().upper() == "USD"
    base_price = settings.PRODUCT_PRICE_USD if is_usd else settings.PRODUCT_PRICE_NAIRA
    late_price = settings.PRODUCT_PRICE_LATE_USD if is_usd else settings.PRODUCT_PRICE_LATE_NAIRA

    amount = base_price
    now = datetime.now(timezone.utc)

    referred_by = None
    if referral_code:
        candidate = referral_code.strip().upper()
        if candidate:
            affiliate = await db.affiliates.find_one({"code": candidate, "active": True})
            if affiliate:
                referred_by = candidate

    existing_lead = await db.leads.find_one({"email": email.lower()})
    is_expired = False
    if existing_lead:
        created_at = existing_lead.get("created_at")
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if (now - created_at).total_seconds() > 24 * 3600:
                is_expired = True
    else:
        if client_expiry:
            if client_expiry < now.timestamp() * 1000:
                is_expired = True

    if is_expired or referred_by:
        amount = late_price

    return amount, referred_by


@router.post("/initialize", response_model=PaymentInitResponse)
@limiter.limit("10/minute")
async def init_payment(body: PaymentInitRequest, request: Request, db=Depends(get_db)):
    """
    Step 1: Determine price, initialize Paystack transaction,
    return authorization/redirect URL.
    """
    reference = f"ACP-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.now(timezone.utc)

    currency = (body.currency or ("USD" if (body.country or "").upper() == "US" else "NGN")).strip().upper()
    amount, referred_by = await compute_price_and_referral(db, body.email, body.client_expiry, body.referral_code, currency=currency)

    # ── Instant affiliate split ────────────────────────────────────────
    # If this affiliate has a Paystack subaccount set up (bank details
    # complete — see services/affiliate_service.py), split the sale at
    # the point of payment instead of tracking it as manual unpaid
    # commission for a later batch transfer. An affiliate without a
    # subaccount yet still works exactly as before.
    subaccount_code = None
    if referred_by:
        referring_affiliate = await db.affiliates.find_one({"code": referred_by, "active": True})
        if referring_affiliate:
            subaccount_code = referring_affiliate.get("subaccount_code")

    # ── Upsert lead ───────────────────────────────────────────────────
    await db.leads.update_one(
        {"email": body.email.lower()},
        {
            "$set": {
                "name": body.name,
                "email": body.email.lower(),
                "source": "landing_page",
                "ip_address": get_real_client_ip(request),
                "converted": False,
                "price_offered": amount,
                "currency": currency,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    payment_method = (body.payment_method or "card" if currency == "USD" else "pay_with_bank").strip().lower()
    channels = None
    if payment_method == "bank_transfer":
        channels = ["bank_transfer"]
    elif payment_method == "card":
        channels = ["card"]

    # Splits settle to an NGN bank account — not meaningful for a USD
    # charge, so a referred USD sale just stays on the manual commission
    # path rather than guessing at untested cross-currency behavior.
    split_applied = bool(subaccount_code) and currency != "USD"

    callback_url = f"{settings.APP_URL}/api/payments/callback"
    try:
        tx_data = await initialize_transaction(
            email=body.email.lower(),
            amount_naira=amount,
            reference=reference,
            callback_url=callback_url,
            metadata={"name": body.name, "payment_method": payment_method, "currency": currency},
            channels=channels,
            currency=currency if currency == "USD" else None,
            subaccount=subaccount_code if split_applied else None,
        )
    except Exception as e:
        err_msg = str(e)
        if currency == "USD" and ("Currency not supported" in err_msg or "currency" in err_msg.lower()):
            print(f"⚠️ Paystack USD not enabled on merchant account: {err_msg}. Falling back to NGN equivalent.")
            ngn_equivalent = amount * settings.USD_TO_NGN_RATE
            try:
                tx_data = await initialize_transaction(
                    email=body.email.lower(),
                    amount_naira=ngn_equivalent,
                    reference=reference,
                    callback_url=callback_url,
                    metadata={"name": body.name, "payment_method": payment_method, "original_currency": "USD", "usd_amount": amount},
                    channels=channels,
                    currency=None,
                )
            except Exception as fallback_err:
                print(f"❌ Paystack initiation fallback error: {fallback_err}")
                raise HTTPException(status_code=502, detail="Payment gateway error. Please try again.")
        else:
            print(f"❌ Paystack initiation error: {e}")
            raise HTTPException(status_code=502, detail="Payment gateway error. Please try again.")

    redirect_url = tx_data.get("authorization_url")
    access_code = tx_data.get("access_code")

    await db.pending_payments.update_one(
        {"reference": reference},
        {"$set": {
            "reference":      reference,
            "charge_id":      access_code,
            "va_id":          None,
            "payment_method": payment_method,
            "email":          body.email.lower(),
            "name":           body.name,
            "amount":         amount,
            "currency":       currency,
            "created_at":     now,
            "referred_by":    referred_by,
            "split_applied":  split_applied,
        }},
        upsert=True,
    )

    return PaymentInitResponse(
        reference=reference,
        charge_id=access_code,
        action="redirect",
        redirect_url=redirect_url,
        amount=amount,
    )


@router.post("/verify", response_model=PaymentVerifyResponse)
@limiter.limit("30/minute")
async def verify_payment(body: PaymentVerifyRequest, request: Request, db=Depends(get_db)):
    """
    Step 2: Frontend polls this after customer claims to have paid.
    Verifies transaction with Paystack, then runs complete_payment().
    """
    existing_payment = await db.payments.find_one({"reference": body.reference, "status": "success"})
    if existing_payment:
        existing_sub = await db.subscribers.find_one({"email": body.email.lower()})
        if existing_sub:
            user = await db.users.find_one({"email": body.email.lower()})
            if user:
                token = create_access_token({"sub": str(user["_id"]), "email": user["email"], "role": "customer"})
                access_token = user.get("library_access_token")
                ml = f"/library?token={access_token}" if access_token else None
                return PaymentVerifyResponse(success=True, token=token, magic_link=ml, amount=existing_payment.get("amount", 0))
        completion = await complete_payment(
            db,
            reference=body.reference,
            email=body.email,
            name=body.name,
            amount=existing_payment.get("amount", 0),
            charge_id=existing_payment.get("charge_id"),
            gateway_response=existing_payment.get("gateway_response", {}),
            completed_via="polling",
            ip_address=get_real_client_ip(request),
            payment_method=body.payment_method,
        )
        ml = f"/library?token={completion['magic_token']}" if completion.get("magic_token") else None
        return PaymentVerifyResponse(success=True, token=completion["token"], magic_link=ml, amount=existing_payment.get("amount", 0))

    try:
        result = await verify_transaction(body.reference)
    except Exception as e:
        print(f"❌ Paystack verify error: {e}")
        return PaymentVerifyResponse(success=False, message="Could not verify payment. Please try again.")

    if not result.get("status"):
        return PaymentVerifyResponse(success=False, message="Payment not yet confirmed. Please wait and try again.")

    data = result.get("data", {})
    if data.get("status") != "success":
        return PaymentVerifyResponse(
            success=False,
            message="Payment not yet confirmed. Please complete payment and try again."
        )

    amount_paid = data.get("amount", 0) / 100.0
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
        charge_id=str(data.get("id")),
        gateway_response=data,
        completed_via="polling",
        ip_address=get_real_client_ip(request),
        payment_method=body.payment_method,
    )

    ml = f"/library?token={completion['magic_token']}" if completion.get("magic_token") else None
    return PaymentVerifyResponse(success=True, token=completion["token"], magic_link=ml, amount=amount_paid)


@router.get("/callback")
async def payment_callback(
    request: Request,
    trxref: str = "",
    reference: str = "",
    db=Depends(get_db),
):
    """
    Paystack redirects here after payment completion.
    Looks up the pending order and redirects to welcome page with token.
    """
    from fastapi.responses import RedirectResponse

    ref = trxref or reference
    if not ref:
        return RedirectResponse("/?error=missing_reference")

    pending = await db.pending_payments.find_one({"reference": ref})
    if not pending:
        return RedirectResponse("/?error=order_not_found")

    try:
        result = await verify_transaction(ref)
        data = result.get("data", {})
    except Exception:
        return RedirectResponse("/?error=verify_failed")

    if not result.get("status") or data.get("status") != "success":
        return RedirectResponse("/?error=payment_not_confirmed")

    email = pending["email"]
    name  = pending["name"]
    amount_paid = data.get("amount", 0) / 100.0

    completion = await complete_payment(
        db,
        reference=ref,
        email=email,
        name=name,
        amount=amount_paid,
        charge_id=str(data.get("id")),
        gateway_response=data,
        completed_via="callback",
        ip_address=get_real_client_ip(request),
        payment_method=pending.get("payment_method", "pay_with_bank"),
    )

    user = await db.users.find_one({"_id": completion["user_id"]})
    access_token = user.get("library_access_token") if user else completion.get("magic_token")
    return RedirectResponse(f"/welcome?token={access_token}")


# ── Webhook processing helper ───────────────────────────────────────────────
async def process_webhook_payment(payload: dict, db):
    t_start = datetime.now(timezone.utc)
    data = payload.get("data", {})
    ref = data.get("reference")
    print(f"⏱ [webhook] start ref={ref} at={t_start.isoformat()}")
    if not ref:
        print("⚠️ Webhook payload missing reference")
        return

    pending = await db.pending_payments.find_one({"reference": ref})
    if not pending:
        if not str(ref).startswith("ACP-"):
            print(f"⚠️ Webhook: Unknown non-ACP reference {ref}")
            return
        await db.flagged_payments.insert_one({
            "reference": ref,
            "reason": "no_matching_pending_payment",
            "payload": data,
            "flagged_at": datetime.now(timezone.utc),
            "resolved": False,
        })
        try:
            flagged_email = data.get("customer", {}).get("email") or "unknown"
            flagged_amount = (data.get("amount") or 0) / 100.0
            await send_email(
                settings.ADMIN_EMAIL,
                f"⚠️ Webhook flagged for manual review — {ref}",
                f"<p>A verified Paystack webhook arrived for reference <b>{ref}</b> "
                f"with no matching pending_payments record.</p>"
                f"<p>Payload claims: email={flagged_email}, amount={flagged_amount}</p>"
                f"<p>No access was granted automatically. Check the flagged_payments "
                f"collection and grant access manually if this is a legitimate payment.</p>",
            )
        except Exception as alert_err:
            print(f"❌ Failed to send manual-review alert for {ref}: {alert_err}")
        print(f"⚠️ Webhook: {ref} has no matching pending_payments record — flagged for manual review, no access granted")
        return
    else:
        email = pending.get("email")
        name = pending.get("name")
        amount_paid = (data.get("amount") or 0) / 100.0 or pending.get("amount", 2000)
        charge_id = str(data.get("id")) or pending.get("charge_id")
        payment_method = pending.get("payment_method")

    if not email:
        print(f"⚠️ Webhook: Missing customer email for {ref}")
        return

    await complete_payment(
        db,
        reference=ref,
        email=email,
        name=name,
        amount=amount_paid,
        charge_id=charge_id,
        gateway_response=data,
        completed_via="webhook",
        payment_method=payment_method,
    )
    t_end = datetime.now(timezone.utc)
    print(f"✅ Webhook: Payment {ref} processed (completion verified/backfilled). "
          f"⏱ [webhook] end ref={ref} at={t_end.isoformat()} elapsed={(t_end - t_start).total_seconds():.3f}s")


# ── Webhook endpoint ──────────────────────────────────────────────────────────
@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    Asynchronous webhook endpoint for Paystack payment completion events.
    Verifies x-paystack-signature (HMAC-SHA512 of request body using secret key).
    """
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    body_text = ""
    try:
        body_text = raw_body.decode("utf-8")
    except Exception as e:
        body_text = f"Error decoding body: {e}"

    log_entry = {
        "received_at": datetime.now(timezone.utc),
        "headers": {k: v for k, v in request.headers.items() if k.lower() != "authorization"},
        "body": body_text,
        "signature_received": signature,
        "ip": get_real_client_ip(request)
    }

    try:
        await db.webhook_logs.insert_one(log_entry)
    except Exception as db_err:
        print(f"❌ Failed to write webhook log to DB: {db_err}")

    secret_key = (settings.PAYSTACK_SECRET_KEY or "").strip()
    if not secret_key:
        print("❌ Webhook rejected: PAYSTACK_SECRET_KEY is not configured on the server")
        raise HTTPException(status_code=500, detail="Webhook verification not configured")

    if not signature:
        print("⚠️ Webhook rejected: x-paystack-signature header missing")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    computed_signature = hmac.new(
        secret_key.encode("utf-8"),
        raw_body,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(signature.strip(), computed_signature):
        print("⚠️ Webhook rejected: Paystack signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event")
    data = payload.get("data", {})
    status = data.get("status")

    print(f"📥 Received Paystack webhook: event={event}, status={status}")

    if event == "charge.success" and status == "success":
        background_tasks.add_task(process_webhook_payment, payload, db)

    return {"status": "received"}
