"""
Single source of truth for "payment confirmed" completion.

Every path that can confirm a Flutterwave payment — the webhook, the
frontend polling /verify endpoint, the redirect /callback, and any manual
reconciliation — must call complete_payment() so a customer always gets
the full sequence: user, payment record, subscriber, all 52 queued emails,
welcome email, and a session token. No caller re-implements these steps.
"""
import asyncio
import secrets
from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from ..config import get_settings
from ..utils.security import create_access_token
from ..workers.email_scheduler import enqueue_sequence_for_subscriber, process_email_queue
from .meta_capi import send_purchase_event

settings = get_settings()


async def complete_payment(
    db,
    *,
    reference: str,
    email: str,
    name: str,
    amount,
    charge_id,
    gateway_response: dict,
    completed_via: str,
    ip_address: str = None,
    payment_method: str = None,
    base_price: float = None,
) -> dict:
    """
    Idempotently complete a confirmed payment. Safe to call more than once
    for the same reference (webhook + frontend poll racing, retries, etc.)
    — the payments.reference unique index is the atomic claim, and the
    subscriber/email-queue check below runs regardless of who wins that
    race, so neither step can be skipped.

    completed_via records which path won the atomic claim ("webhook",
    "polling", "callback", "manual_reconciliation") — set once, at insert
    time, never overwritten by a later caller that finds it already claimed.

    Returns {"user_id": ObjectId, "token": str, "already_completed": bool}.
    """
    email = email.lower()
    now = datetime.now(timezone.utc)
    amount_charged = float(amount or 0)

    # ── Resolve base product price ─────────────────────────────────────
    # Commission, revenue reporting, and refunds must ALWAYS calculate on
    # the product's base price — NOT the raw gateway amount charged, which
    # can include Paystack processing fees, bank transfer surcharges, etc.
    pending = await db.pending_payments.find_one({"reference": reference})
    currency = (pending.get("currency") if pending else None) or ("USD" if gateway_response.get("currency") == "USD" else "NGN")

    if base_price is not None:
        resolved_base_price = float(base_price)
    elif pending and pending.get("base_price") is not None:
        resolved_base_price = float(pending["base_price"])
    elif pending and pending.get("amount") is not None:
        resolved_base_price = float(pending["amount"])
    else:
        # Fallback if pending record is somehow missing
        if currency == "USD":
            resolved_base_price = float(settings.USD_PRICE)
        elif amount_charged >= 4500:
            resolved_base_price = float(settings.PRODUCT_PRICE_LATE_NAIRA)
        else:
            resolved_base_price = float(settings.PRODUCT_PRICE_NAIRA)

    # ── Atomically claim this reference ────────────────────────────────
    # The unique index on payments.reference (see database.py) makes this
    # the real concurrency guard, unlike a find-then-insert check which
    # has a race window between the read and the write.
    commission_base = float(pending.get("commission_base_price", resolved_base_price) if pending else resolved_base_price)
    friend_discount_applied = bool(pending.get("friend_discount_applied", False)) if pending else False
    friend_emails = list(pending.get("friend_emails", [])) if pending else []

    try:
        await db.payments.insert_one({
            "reference": reference,
            "charge_id": charge_id,
            "email": email,
            "name": name,
            "base_price": resolved_base_price,
            "commission_base_price": commission_base,
            "amount_charged": amount_charged,
            "amount": resolved_base_price,
            "amount_paid": amount_charged or resolved_base_price,
            "currency": currency,
            "gateway": "paystack",
            "payment_method": payment_method,
            "status": "success",
            "gateway_response": gateway_response,
            "verified_at": now,
            "created_at": now,
            "purchase_date": now,
            "ip_address": ip_address,
            "completed_via": completed_via,
            "tier": (pending.get("tier") if pending else "complete"),
            "friend_discount_applied": friend_discount_applied,
            "friend_emails": friend_emails,
        })
        claimed = True
    except DuplicateKeyError:
        claimed = False
    print(f"⏱ [complete_payment] ref={reference} claimed={claimed} via={completed_via} at={now.isoformat()}")

    # ── Resolve Tier & Product Entitlements ────────────────────────────
    tier = (pending.get("tier") if pending else None) or "complete"
    user = await db.users.find_one({"email": email})
    
    current_products = user.get("purchased_products", []) if user else []
    already_has_all = "all" in current_products
    
    if tier == "starter" and not already_has_all:
        starter_prods = await db.products.find({"order": {"$in": [1, 2]}}).to_list(10)
        starter_ids = [str(p["_id"]) for p in starter_prods]
        new_products = list(set(current_products + starter_ids))
    else:
        new_products = ["all"]
        
    is_vip = True if tier == "vip" or (user and user.get("is_vip")) else False
    user_tier = "vip" if is_vip else ("complete" if "all" in new_products else tier)

    # ── Create or get the user ─────────────────────────────────────────
    access_token = secrets.token_urlsafe(32)
    if not user:
        ins = await db.users.insert_one({
            "name": name,
            "email": email,
            "role": "customer",
            "created_at": now,
            "purchase_date": now,
            "last_login": now,
            "is_active": True,
            "purchased_products": new_products,
            "tier": user_tier,
            "is_vip": is_vip,
            "library_access_token": access_token,
        })
        user_id = ins.inserted_id
    else:
        user_id = user["_id"]
        access_token = user.get("library_access_token")
        update_doc = {
            "last_login": now,
            "purchased_products": new_products,
            "tier": user_tier,
            "is_vip": is_vip,
        }
        if not access_token:
            access_token = secrets.token_urlsafe(32)
            update_doc["library_access_token"] = access_token
        await db.users.update_one({"_id": user_id}, {"$set": update_doc})

    if claimed:
        await db.payments.update_one({"reference": reference}, {"$set": {"user_id": user_id}})
        await db.leads.update_one(
            {"email": email},
            {"$set": {"converted": True, "conversion_date": now}},
        )

        # ── Abandoned Transaction Recovery ──────────────────────────────
        from .abandoned_recovery_service import mark_transaction_recovered
        await mark_transaction_recovered(db, email=email, reference=reference)


        # ── Referral attribution ────────────────────────────────────────
        # Only recorded on the winning claim — a retry/race that finds the
        # payment already claimed must not double-count the same sale
        # against the affiliate. referred_by was captured at checkout time
        # (see routes/payments.py) and lives on the matching
        # pending_payments doc. The commission rate is locked in at the
        # affiliate's *current* rate at this exact moment — a later edit
        # to their rate never retroactively changes what this sale owes.
        # CRITICAL RULE: Commission is ALWAYS computed on commission_base_price (₦5,000), method-agnostic.
        referred_by = pending.get("referred_by") if pending else None
        if referred_by:
            affiliate = await db.affiliates.find_one({"code": referred_by, "active": True})
            if affiliate:
                rate = float(
                    affiliate.get("commission_percent", settings.DEFAULT_AFFILIATE_COMMISSION_PERCENT) 
                    or settings.DEFAULT_AFFILIATE_COMMISSION_PERCENT
                )
                if pending and pending.get("affiliate_commission_override") is not None:
                    commission_amount = float(pending["affiliate_commission_override"])
                else:
                    commission_amount = round(commission_base * rate / 100, 2)

                # split_applied means Paystack already sent the affiliate
                # their cut directly at the point of payment (see
                # routes/payments.py + services/affiliate_service.py).
                # Recorded as commission_status="paid" with payout_method distinguishing how.
                split_applied = bool(pending.get("split_applied")) if pending else False
                try:
                    await db.referrals.insert_one({
                        "reference": reference,
                        "affiliate_code": referred_by,
                        "email": email,
                        "name": name,
                        "base_price": commission_base,
                        "commission_base_price": commission_base,
                        "amount_charged": amount_charged,
                        "amount_paid": amount_charged or resolved_base_price,
                        "amount": resolved_base_price,
                        "currency": currency,
                        "commission_rate": rate,
                        "commission_amount": commission_amount,
                        "commission_status": "paid" if split_applied else "unpaid",
                        "payout_method": "instant_split" if split_applied else "manual_batch",
                        "paid_at": now if split_applied else None,
                        "created_at": now,
                        "friend_discount_applied": friend_discount_applied,
                        "friend_emails": friend_emails,
                    })
                except DuplicateKeyError:
                    pass

                # ── Check and Trigger 10-Sale Milestone / Recruiter Bonuses ───
                from .affiliate_milestone_service import check_and_trigger_milestones
                await check_and_trigger_milestones(db, referred_by)

        # ── Viral Referral Leads (Saved ONLY after payment is verified) ──
        # Guarantees abandoned checkouts never gain entry into referral_leads.
        # Idempotent via unique index on friend_email.
        if friend_emails and isinstance(friend_emails, list):
            for fe in friend_emails:
                if not fe or not isinstance(fe, str):
                    continue
                fe_clean = fe.strip().lower()
                try:
                    await db.referral_leads.insert_one({
                        "friend_email": fe_clean,
                        "referred_by": email,
                        "order_reference": reference,
                        "affiliate_code": referred_by,
                        "created_at": now,
                        "status": "new",
                    })
                except DuplicateKeyError:
                    # Same friend was already referred by an earlier buyer.
                    # Keep track of first referrer as per spec.
                    pass

        # Server-side conversion confirmation — fires exactly once per
        # real payment (guarded by `claimed`, same as everything else in
        # this block), independent of whether the customer's browser ever
        # runs the client-side Pixel fire in checkout.js. Same event_id
        # (reference) as that client-side fire, so Meta deduplicates them
        # into one conversion rather than counting twice. No-ops safely if
        # FB_CAPI_ACCESS_TOKEN isn't configured.
        capi_result = await send_purchase_event(
            email=email, amount=resolved_base_price, reference=reference, ip_address=ip_address,
        )
        await db.payments.update_one({"reference": reference}, {"$set": {"capi_result": capi_result}})
        if capi_result.get("sent"):
            print(f"✅ Meta CAPI Purchase event sent for {reference}")
        else:
            print(f"⚠️ Meta CAPI Purchase event not sent for {reference}: {capi_result.get('reason')}")

    # ── Subscriber + 52-email queue ────────────────────────────────────
    # This is the safety net: run regardless of `claimed`, so a payment
    # that another caller already marked "success" can never leave a
    # customer without a subscriber record or queued emails.
    existing_sub = await db.subscribers.find_one({"email": email})
    if not existing_sub:
        unsub_token = secrets.token_urlsafe(32)
        sub_result = await db.subscribers.insert_one({
            "name": name,
            "email": email,
            "subscribed_at": now,
            "sequence_position": 0,
            "next_send_at": now,
            "is_active": True,
            "tags": ["buyer"],
            "payment_reference": reference,
            "unsubscribe_token": unsub_token,
        })
        await enqueue_sequence_for_subscriber(sub_result.inserted_id, now)
        subscriber_created = True
    else:
        unsub_token = existing_sub.get("unsubscribe_token", "")
        subscriber_created = False
        # A free WhatsApp-community joiner who later actually buys must be
        # upgraded from the short community nurture sequence to the full
        # 52-email paid curriculum — otherwise they'd be stuck on the free
        # sequence forever, since new subscribers are only ever created once.
        if claimed and "buyer" not in existing_sub.get("tags", []):
            await db.subscribers.update_one(
                {"_id": existing_sub["_id"]},
                {"$addToSet": {"tags": "buyer"}},
            )
            await db.email_queue.update_many(
                {
                    "subscriber_id": existing_sub["_id"],
                    "kind": "sequence",
                    "status": {"$in": ["pending", "retry"]},
                },
                {"$set": {"status": "skipped"}},
            )
            await enqueue_sequence_for_subscriber(existing_sub["_id"], now)

    # ── Welcome email ──────────────────────────────────────────────────
    # Only send once: either this call claimed the payment, or it found
    # the payment already claimed but the subscriber missing (the exact
    # gap this refactor closes).
    queued_email = False
    if claimed or subscriber_created:
        # ── Auto-Provision Buyer as VIP Ambassador & Affiliate ──────────
        aff_code = None
        aff_token = None
        try:
            from .affiliate_service import get_or_create_customer_affiliate
            customer_affiliate, _ = await get_or_create_customer_affiliate(
                db,
                name=name,
                email=email,
                invited_by=referred_by,
            )
            if customer_affiliate:
                aff_code = customer_affiliate.get("code")
                aff_token = customer_affiliate.get("dashboard_token")
        except Exception as e:
            print(f"⚠️ Failed to auto-provision affiliate for buyer {email}: {e}")

        referral_link = f"https://edgepack.thescaleconference.com/?ref={aff_code}" if aff_code else None
        recruiter_link = f"https://edgepack.thescaleconference.com/affiliate/register?invite={aff_code}" if aff_code else None
        dashboard_link = f"{settings.APP_URL}/affiliate/dashboard?token={aff_token}" if aff_token else f"{settings.APP_URL}/affiliate/dashboard"

        # Tracked the same way as sequence emails, so a transient SMTP
        # failure gets automatically retried by the 5-minute scheduler
        # instead of silently vanishing with no record it ever failed.
        await db.email_queue.insert_one({
            "kind": "welcome",
            "user_id": user_id,
            "email": email,
            "name": name,
            "access_token": access_token,
            "unsubscribe_token": unsub_token,
            "affiliate_code": aff_code,
            "referral_link": referral_link,
            "recruiter_link": recruiter_link,
            "dashboard_link": dashboard_link,
            "scheduled_at": now,
            "status": "pending",
            "retry_count": 0,
            "sent_at": None,
            "error": None,
        })
        queued_email = True

    if queued_email or subscriber_created:
        # Attempt immediately (welcome email and/or first drip email);
        # fire-and-forget so the SMTP round trip never delays the
        # caller's response — the scheduler retries anything left pending.
        asyncio.create_task(process_email_queue())

    jwt_token = create_access_token({"sub": str(user_id), "email": email, "role": "customer"})
    return {"user_id": user_id, "token": jwt_token, "magic_token": access_token, "already_completed": not claimed}
