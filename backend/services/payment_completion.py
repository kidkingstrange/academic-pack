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


async def complete_payment(
    db,
    *,
    reference: str,
    email: str,
    name: str,
    amount,
    charge_id,
    gateway_response: dict,
    ip_address: str = None,
) -> dict:
    """
    Idempotently complete a confirmed payment. Safe to call more than once
    for the same reference (webhook + frontend poll racing, retries, etc.)
    — the payments.reference unique index is the atomic claim, and the
    subscriber/email-queue check below runs regardless of who wins that
    race, so neither step can be skipped.

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
            "gateway": "flutterwave",
            "status": "success",
            "gateway_response": gateway_response,
            "verified_at": now,
            "created_at": now,
            "ip_address": ip_address,
        })
        claimed = True
    except DuplicateKeyError:
        claimed = False

    # ── Create or get the user ─────────────────────────────────────────
    user = await db.users.find_one({"email": email})
    if not user:
        ins = await db.users.insert_one({
            "name": name,
            "email": email,
            "role": "customer",
            "created_at": now,
            "last_login": now,
            "is_active": True,
            "purchased_products": ["all"],
        })
        user_id = ins.inserted_id
    else:
        user_id = user["_id"]
        await db.users.update_one({"_id": user_id}, {"$set": {"last_login": now}})

    if claimed:
        await db.payments.update_one({"reference": reference}, {"$set": {"user_id": user_id}})
        await db.leads.update_one(
            {"email": email},
            {"$set": {"converted": True, "conversion_date": now}},
        )

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

    # ── Magic link + welcome email ─────────────────────────────────────
    # Only send once: either this call claimed the payment, or it found
    # the payment already claimed but the subscriber missing (the exact
    # gap this refactor closes).
    queued_email = False
    if claimed or subscriber_created:
        magic_token = secrets.token_urlsafe(32)
        await db.magic_links.insert_one({
            "token": magic_token,
            "user_id": user_id,
            "purpose": "welcome",
            "expires_at": now + timedelta(days=90),
            "used": False,
            "created_at": now,
        })
        # Tracked the same way as sequence emails, so a transient SMTP
        # failure gets automatically retried by the 5-minute scheduler
        # instead of silently vanishing with no record it ever failed.
        await db.email_queue.insert_one({
            "kind": "welcome",
            "user_id": user_id,
            "email": email,
            "name": name,
            "magic_token": magic_token,
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
    return {"user_id": user_id, "token": jwt_token, "already_completed": not claimed}
