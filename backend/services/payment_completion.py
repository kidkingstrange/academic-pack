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

from ..utils.security import create_access_token
from ..workers.email_scheduler import enqueue_sequence_for_subscriber, process_email_queue
from .meta_capi import send_purchase_event


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

    # ── Atomically claim this reference ────────────────────────────────
    # The unique index on payments.reference (see database.py) makes this
    # the real concurrency guard, unlike a find-then-insert check which
    # has a race window between the read and the write.
    try:
        await db.payments.insert_one({
            "reference": reference,
            "charge_id": charge_id,
            "email": email,
            "name": name,
            "amount": amount,
            "currency": "NGN",
            "gateway": "paystack",
            "payment_method": payment_method,
            "status": "success",
            "gateway_response": gateway_response,
            "verified_at": now,
            "created_at": now,
            "ip_address": ip_address,
            "completed_via": completed_via,
        })
        claimed = True
    except DuplicateKeyError:
        claimed = False
    print(f"⏱ [complete_payment] ref={reference} claimed={claimed} via={completed_via} at={now.isoformat()}")

    # ── Create or get the user ─────────────────────────────────────────
    user = await db.users.find_one({"email": email})
    access_token = secrets.token_urlsafe(32)
    if not user:
        ins = await db.users.insert_one({
            "name": name,
            "email": email,
            "role": "customer",
            "created_at": now,
            "last_login": now,
            "is_active": True,
            "purchased_products": ["all"],
            "library_access_token": access_token,
        })
        user_id = ins.inserted_id
    else:
        user_id = user["_id"]
        access_token = user.get("library_access_token")
        if not access_token:
            access_token = secrets.token_urlsafe(32)
            await db.users.update_one({"_id": user_id}, {"$set": {"last_login": now, "library_access_token": access_token}})
        else:
            await db.users.update_one({"_id": user_id}, {"$set": {"last_login": now}})

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
        pending = await db.pending_payments.find_one({"reference": reference})
        referred_by = pending.get("referred_by") if pending else None
        if referred_by:
            affiliate = await db.affiliates.find_one({"code": referred_by, "active": True})
            if affiliate:
                rate = affiliate.get("commission_percent", 0) or 0
                commission_amount = round(amount * rate / 100, 2)
                # split_applied means Paystack already sent the affiliate
                # their cut directly at the point of payment (see
                # routes/payments.py + services/affiliate_service.py).
                # Recorded as commission_status="paid" (it genuinely is —
                # every existing "commission paid" total across the admin
                # and affiliate dashboards does an exact match on "paid")
                # with payout_method distinguishing how, purely for audit
                # visibility. Critically, this also means
                # build_pending_batch()'s {"commission_status": "unpaid"}
                # query skips it — without that, the affiliate would be
                # paid twice: once instantly via the split, once again in
                # the next manual batch transfer.
                split_applied = bool(pending.get("split_applied")) if pending else False
                try:
                    await db.referrals.insert_one({
                        "reference": reference,
                        "affiliate_code": referred_by,
                        "email": email,
                        "name": name,
                        "amount": amount,
                        "commission_rate": rate,
                        "commission_amount": commission_amount,
                        "commission_status": "paid" if split_applied else "unpaid",
                        "payout_method": "instant_split" if split_applied else "manual_batch",
                        "paid_at": now if split_applied else None,
                        "created_at": now,
                    })
                except DuplicateKeyError:
                    pass

        # Server-side conversion confirmation — fires exactly once per
        # real payment (guarded by `claimed`, same as everything else in
        # this block), independent of whether the customer's browser ever
        # runs the client-side Pixel fire in checkout.js. Same event_id
        # (reference) as that client-side fire, so Meta deduplicates them
        # into one conversion rather than counting twice. No-ops safely if
        # FB_CAPI_ACCESS_TOKEN isn't configured.
        capi_result = await send_purchase_event(
            email=email, amount=amount, reference=reference, ip_address=ip_address,
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
