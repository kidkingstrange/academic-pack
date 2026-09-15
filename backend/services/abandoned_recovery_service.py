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
    tier: str = "complete",
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
        "tier": tier or "complete",
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

    query["status"] = {"$in": ["pending", "sequence_active", "daily_drip_active", "abandoned"]}

    # Identify any active bonuses based on current sequence step before recovering
    abandoned_tx = await db.abandoned_transactions.find_one(query)
    earned_bonuses = []
    if abandoned_tx:
        step = abandoned_tx.get("sequence_step", 1)
        if step <= 2:
            earned_bonuses.append("The 3.0 to 4.5 GPA Active Retrieval Audio Cram Protocol")
        if step <= 7:
            earned_bonuses.append("72-Hour Semester Exam Survival Template + Emergency Worksheets")
        if step <= 9:
            earned_bonuses.append("Priority VIP WhatsApp Strategy Pass")
        if step >= 10:
            earned_bonuses.append("Emergency Comeback Flashcard Vault")

    res = await db.abandoned_transactions.update_many(
        query,
        {
            "$set": {
                "status": "recovered",
                "recovered_at": now,
                "recovered_reference": recovered_reference or reference,
                "earned_bonuses": earned_bonuses,
                "updated_at": now,
            }
        },
    )

    if earned_bonuses and email:
        await db.users.update_one(
            {"email": email.strip().lower()},
            {"$addToSet": {"earned_bonuses": {"$each": earned_bonuses}}},
        )

    return res.modified_count


DAILY_TOPICS = [
    {
        "subject": "The optical illusion of re-reading lecture slides, {name}",
        "subtitle": "Why studying 8 hours with highlighters still leads to exam hall panic.",
        "headline": "Why 'feeling familiar' with a topic is killing your exam grades.",
        "body": "<p>When you read a lecture slide 4 times, your brain recognizes the words and gives you a false dopamine signal: <em>'I know this.'</em></p><p>Then exam day comes. The question asks you to apply the concept or derive the formula from a blank sheet of paper, and your brain completely freezes.</p><p>Psychologists call this the <strong>Fluency Illusion</strong>. In the <em>Academic Comeback Package</em>, you learn how to test retrieval every 15 minutes using the Active Retrieval Protocol so information is burned into long-term synaptic memory.</p>",
    },
    {
        "subject": "How to study 3 hours and outperform 10-hour crammers, {name}",
        "subtitle": "The cognitive difference between active extraction and passive absorption.",
        "headline": "Why top students never study until 4:00 AM.",
        "body": "<p>Have you ever noticed that the top student in your department often looks relaxed, plays sports, and sleeps early before exam days?</p><p>They aren't genetically superior. They use <strong>Spaced High-Yield Encoding</strong>. Rather than rereading 300-page textbooks, they use structured concept maps and self-testing matrices.</p><p>You can start using this exact framework tonight for less than the cost of a plate of food.</p>",
    },
    {
        "subject": "The 10-minute cure for exam room blank-outs, {name}",
        "subtitle": "What to do the second stress cortisol blocks your hippocampus during exams.",
        "headline": "Never stare blankly at an exam paper again.",
        "body": "<p>When you sit in the hall and feel your heart beating fast, cortisol floods your prefrontal cortex and physically blocks your memory retrieval pathways.</p><p>Inside the <em>Exam Survival Protocol</em> (Guide #3 of the Academic Comeback Package), you get the physical 60-second breathing and neural grounding sequence that resets your memory engine in under a minute.</p>",
    },
    {
        "subject": "Did you surrender your semester, {name}? (Let's be real)",
        "subtitle": "No matter how low your GPA dropped, there is still time to recover.",
        "headline": "A bad past semester does not define your graduation class.",
        "body": "<p>I have worked with students who thought they were heading straight for probation, who turned their grades around in a single 12-week semester by changing their study systems.</p><p>Don't let another week of lecture notes pile up without an effective study protocol.</p>",
    },
]


async def send_recovery_email_step(db, tx: dict, step: int) -> bool:
    """
    Send Step 1 through 9, or Daily Drip (Step 10+) recovery email to the customer.
    """
    email = tx.get("email")
    name = tx.get("name") or "Student"
    reference = tx.get("reference")
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

    currency_symbol = "$" if currency == "USD" else "₦"
    is_usd = currency == "USD"
    starter_amount = float(settings.TIER_STARTER_PRICE_USD if is_usd else settings.TIER_STARTER_PRICE_NAIRA)
    complete_amount = float(settings.TIER_COMPLETE_PRICE_USD if is_usd else settings.TIER_COMPLETE_PRICE_NAIRA)
    vip_amount = float(settings.TIER_VIP_PRICE_USD if is_usd else settings.TIER_VIP_PRICE_NAIRA)

    starter_url = f"{settings.APP_URL}/api/payments/recovery-redirect?ref={reference}&tier=starter"
    complete_url = f"{settings.APP_URL}/api/payments/recovery-redirect?ref={reference}&tier=complete"
    vip_url = f"{settings.APP_URL}/api/payments/recovery-redirect?ref={reference}&tier=vip"
    recovery_url = complete_url
    unsubscribe_url = f"{settings.APP_URL}/api/payments/abandoned/unsubscribe?token={unsub_token}"

    context = {
        "name": name,
        "amount": complete_amount,
        "starter_amount": starter_amount,
        "complete_amount": complete_amount,
        "vip_amount": vip_amount,
        "starter_url": starter_url,
        "complete_url": complete_url,
        "vip_url": vip_url,
        "currency": currency,
        "currency_symbol": currency_symbol,
        "recovery_url": recovery_url,
        "unsubscribe_token": unsub_token,
        "unsubscribe_url": unsubscribe_url,
        "app_url": settings.APP_URL,
    }

    subjects = {
        1: f"Did your payment get stuck, {name}? (+ 2-Hour Audio Cram Bonus)",
        2: f"⏰ [Final 30 Mins] Your 2-Hour Audio Cram Bonus is expiring, {name}",
        3: f"Is this what's holding you back, {name}? (Honest question)",
        4: f"Tonight before you sleep, {name}...",
        5: f"🎁 [New Day 2 Bonus Unlocked] 72-Hour Exam Survival Template, {name}",
        6: f"The brutal math of carrying over one course (Read this, {name})",
        7: f"Midnight Deadline: Day 2 Bonus Vault is closing, {name}",
        8: f"Releasing your cart reservation to the waitlist, {name}",
        9: f"Final Notice: VIP Strategy Pass added for tonight only, {name}",
    }

    if step <= 9:
        template_name = f"abandoned_recovery_{step}.html"
        subject = subjects.get(step, f"Complete your Academic Comeback, {name}")
    else:
        template_name = "abandoned_recovery_daily.html"
        topic_idx = (step - 10) % len(DAILY_TOPICS)
        topic = DAILY_TOPICS[topic_idx]
        subject = topic["subject"].format(name=name)
        context["daily_subject"] = subject
        context["daily_subtitle"] = topic["subtitle"]
        context["daily_headline"] = topic["headline"]
        context["daily_body"] = topic["body"]

    try:
        html_content = render_template(template_name, context)
    except Exception as e:
        print(f"❌ Error rendering recovery template {template_name}: {e}")
        return False

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


async def backfill_unconverted_leads(db) -> int:
    """
    Backfill any unconverted leads from db.leads into db.abandoned_transactions.
    Skips customers who have already purchased or are already in abandoned_transactions.
    """
    import uuid
    now = datetime.now(timezone.utc)
    
    # Pre-fetch all buyers and existing abandoned emails in single fast batch queries
    paid_emails = {p.get("email", "").strip().lower() for p in await db.payments.find({"status": "success"}, {"email": 1}).to_list(5000)}
    user_buyers = {u.get("email", "").strip().lower() for u in await db.users.find({"purchased_products": {"$exists": True, "$ne": []}}, {"email": 1}).to_list(5000)}
    all_buyers = paid_emails.union(user_buyers)
    
    existing_abandoned = {a.get("email", "").strip().lower() for a in await db.abandoned_transactions.find({}, {"email": 1}).to_list(5000)}
    
    unconverted_leads = await db.leads.find({"converted": False}).to_list(length=1000)
    
    backfilled_count = 0
    for lead in unconverted_leads:
        email = lead.get("email", "").strip().lower()
        if not email or "@" not in email:
            continue
            
        if email in all_buyers:
            await db.leads.update_one({"_id": lead["_id"]}, {"$set": {"converted": True, "conversion_date": now}})
            continue
            
        if email in existing_abandoned:
            continue
            
        ref = f"ACP-{uuid.uuid4().hex[:12].upper()}"
        amount = lead.get("price_offered") or settings.PRODUCT_PRICE_NAIRA
        currency = (lead.get("currency") or "NGN").upper()
        unsub_token = secrets.token_urlsafe(32)
        
        created_at = lead.get("created_at") or now
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except Exception:
                created_at = now
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
            
        doc = {
            "reference": ref,
            "email": email,
            "name": lead.get("name") or "Valued Student",
            "amount": float(amount),
            "currency": currency,
            "payment_method": "bank_transfer",
            "referred_by": lead.get("referred_by"),
            "created_at": created_at,
            "updated_at": now,
            "status": "pending",
            "sequence_step": 0,
            "next_email_at": None,
            "last_email_sent_at": None,
            "emails_sent": [],
            "unsubscribe_token": unsub_token,
            "source": "lead_backfill",
        }
        await db.abandoned_transactions.insert_one(doc)
        backfilled_count += 1
        
    return backfilled_count

