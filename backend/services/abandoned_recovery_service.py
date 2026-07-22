"""
Abandoned Transaction Recovery Service.
Handles tracking, deduplication, buyer checks, email delivery, and status updates.
"""
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ..config import get_settings
from ..services.email_service import send_email, render_template

settings = get_settings()


async def is_buyer(db, email: str) -> bool:
    """Check if customer has already successfully purchased."""
    email_clean = email.strip().lower()
    
    # 1. Check successful payments
    paid = await db.payments.find_one({"email": email_clean, "status": "success"})
    if paid:
        return True

    # 2. Check users with purchased products
    user = await db.users.find_one({"email": email_clean, "purchased_products": {"$exists": True, "$ne": []}})
    if user:
        return True

    # 3. Check subscribers with buyer tag
    sub = await db.subscribers.find_one({"email": email_clean, "tags": "buyer"})
    if sub:
        return True

    return False


async def is_unsubscribed(db, email: str) -> bool:
    """Check if customer unsubscribed from recovery emails."""
    email_clean = email.strip().lower()
    unsub = await db.recovery_unsubscribes.find_one({"email": email_clean})
    return bool(unsub)


async def unsubscribe_email(db, email: str) -> None:
    """Record an unsubscribe request for recovery emails."""
    email_clean = email.strip().lower()
    now = datetime.now(timezone.utc)
    await db.recovery_unsubscribes.update_one(
        {"email": email_clean},
        {"$set": {"email": email_clean, "unsubscribed_at": now}},
        upsert=True,
    )
    # Cancel any active recovery sequences for this email
    await db.abandoned_transactions.update_many(
        {"email": email_clean, "status": {"$in": ["pending", "sequence_active"]}},
        {"$set": {"status": "unsubscribed", "updated_at": now}},
    )


async def record_checkout_initialization(
    db,
    *,
    email: str,
    name: str,
    amount: float,
    currency: str,
    reference: str,
    payment_method: str = "pay_with_bank",
    referred_by: Optional[str] = None,
    source: str = "checkout_init",
) -> Dict[str, Any]:
    """
    Record or update a checkout initialization in db.abandoned_transactions.
    """
    email_clean = email.strip().lower()
    now = datetime.now(timezone.utc)

    # Cancel any older pending or sequence_active attempts for this email to avoid duplicates
    await db.abandoned_transactions.update_many(
        {"email": email_clean, "reference": {"$ne": reference}, "status": {"$in": ["pending", "sequence_active"]}},
        {"$set": {"status": "superseded", "updated_at": now}},
    )

    unsub_token = secrets.token_urlsafe(32)

    doc = {
        "reference": reference,
        "email": email_clean,
        "name": name or "Valued Student",
        "amount": amount,
        "currency": (currency or "NGN").upper(),
        "payment_method": payment_method,
        "referred_by": referred_by,
        "created_at": now,
        "updated_at": now,
        "status": "pending",
        "sequence_step": 0,
        "next_email_at": None,
        "last_email_sent_at": None,
        "emails_sent": [],
        "unsubscribe_token": unsub_token,
        "source": source,
    }

    await db.abandoned_transactions.update_one(
        {"reference": reference},
        {"$set": doc},
        upsert=True,
    )

    return doc


async def mark_transaction_recovered(
    db,
    *,
    email: str = None,
    reference: str = None,
    recovered_reference: str = None,
) -> int:
    """
    Mark abandoned transaction(s) as recovered when payment completes.
    """
    now = datetime.now(timezone.utc)
    query = {}
    if reference:
        query["reference"] = reference
    elif email:
        query["email"] = email.strip().lower()
    else:
        return 0

    query["status"] = {"$in": ["pending", "sequence_active", "abandoned"]}

    res = await db.abandoned_transactions.update_many(
        query,
        {
            "$set": {
                "status": "recovered",
                "recovered_at": now,
                "recovered_reference": recovered_reference or reference,
                "updated_at": now,
            }
        },
    )
    return res.modified_count


async def send_recovery_email_step(db, tx: dict, step: int) -> bool:
    """
    Send Step 1, 2, or 3 recovery email to the customer.
    """
    email = tx.get("email")
    name = tx.get("name") or "Student"
    reference = tx.get("reference")
    amount = tx.get("amount", 2000.0)
    currency = tx.get("currency", "NGN").upper()
    unsub_token = tx.get("unsubscribe_token") or ""

    # Verify stop conditions before sending
    if await is_buyer(db, email):
        await mark_transaction_recovered(db, email=email)
        return False

    if await is_unsubscribed(db, email):
        await db.abandoned_transactions.update_one(
            {"reference": reference},
            {"$set": {"status": "unsubscribed", "updated_at": datetime.now(timezone.utc)}}
        )
        return False


    if step == 4:
        amount = settings.ABANDONED_STEP4_PRICE_USD if currency == "USD" else settings.ABANDONED_STEP4_PRICE_NAIRA

    currency_symbol = "$" if currency == "USD" else "₦"
    recovery_url = f"{settings.APP_URL}/api/payments/recovery-redirect?ref={reference}"
    unsubscribe_url = f"{settings.APP_URL}/api/payments/abandoned/unsubscribe?token={unsub_token}"

    context = {
        "name": name,
        "amount": amount,
        "currency": currency,
        "currency_symbol": currency_symbol,
        "recovery_url": recovery_url,
        "unsubscribe_token": unsub_token,
        "unsubscribe_url": unsubscribe_url,
        "app_url": settings.APP_URL,
        "discount_enabled": settings.ABANDONED_DISCOUNT_ENABLED if step == 3 else False,
        "discount_percent": settings.ABANDONED_DISCOUNT_PERCENT,
        "discount_code": settings.ABANDONED_DISCOUNT_CODE,
    }

    template_name = f"abandoned_recovery_{step}.html"
    try:
        html_content = render_template(template_name, context)
    except Exception as e:
        print(f"❌ Error rendering recovery template {template_name}: {e}")
        return False

    subjects = {
        1: f"You left something behind, {name}!",
        2: f"Your Academic Comeback Package is still reserved, {name}",
        3: f"Final Reminder: Complete your Academic Comeback, {name}",
        4: f"Special Re-Open: Get your Academic Comeback Package for {currency_symbol}{amount:,.2f}, {name}",
    }
    subject = subjects.get(step, f"Complete your purchase, {name}")


    success, error = await send_email(email, subject, html_content)
    now = datetime.now(timezone.utc)

    log_entry = {
        "step": step,
        "sent_at": now,
        "subject": subject,
        "success": success,
        "error": error,
    }

    update_payload = {
        "last_email_sent_at": now,
        "sequence_step": step,
        "updated_at": now,
    }

    if success:
        print(f"📧 Recovery Email Step {step} sent to {email} (ref: {reference})")
    else:
        print(f"❌ Failed to send Recovery Email Step {step} to {email}: {error}")

    await db.abandoned_transactions.update_one(
        {"reference": reference},
        {
            "$set": update_payload,
            "$push": {"emails_sent": log_entry},
        },
    )


    return success
