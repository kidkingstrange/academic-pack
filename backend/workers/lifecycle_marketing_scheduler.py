"""
Background Worker: Lifecycle Marketing & Automated Retention Scheduler.
Manages post-purchase cross-sell ascension drips, dormant customer win-backs,
and automated weekly broadcasts (Tuesday Value / Friday Direct Response).
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .. import database
from ..config import get_settings
from ..services.marketing_service import (
    PRODUCT_KNOWLEDGE_BASE,
    get_product_by_slug,
    generate_ai_campaign_copy,
    get_suppression_set,
    recommend_cross_sell_product,
)

settings = get_settings()
scheduler = AsyncIOScheduler()


async def get_marketing_settings(db) -> Dict[str, Any]:
    """Retrieve runtime automation toggles from database or return defaults."""
    default_settings = {
        "post_purchase_cross_sell_enabled": True,
        "win_back_enabled": True,
        "weekly_broadcast_enabled": False,  # Manual or auto-cadence
        "max_marketing_per_user_per_week": 2,
    }
    if db is None:
        return default_settings

    doc = await db.marketing_settings.find_one({"key": "global_config"})
    if doc:
        return {**default_settings, **doc.get("settings", {})}
    return default_settings


async def update_marketing_settings(db, new_settings: Dict[str, Any]) -> Dict[str, Any]:
    """Update runtime automation toggles in database."""
    current = await get_marketing_settings(db)
    merged = {**current, **new_settings}
    if db is not None:
        now = datetime.now(timezone.utc)
        await db.marketing_settings.update_one(
            {"key": "global_config"},
            {"$set": {"settings": merged, "updated_at": now}},
            upsert=True
        )
    return merged


async def run_lifecycle_cross_sell_scan() -> Dict[str, int]:
    """
    Scans recent buyers to schedule personalized, high-affinity cross-sell emails.
    - Day 7 (+/- 2 days): First complementary cross-sell
    - Day 21 (+/- 3 days): Second complementary cross-sell
    - Day 60 (+): Dormant customer win-back
    Strictly excludes already-purchased books and unsubscribed recipients.
    """
    db = database.get_db()
    if db is None:
        return {"scanned": 0, "enqueued": 0}

    cfg = await get_marketing_settings(db)
    if not cfg.get("post_purchase_cross_sell_enabled", True):
        return {"scanned": 0, "enqueued": 0, "skipped_reason": "disabled"}

    suppressed = await get_suppression_set(db)
    now = datetime.now(timezone.utc)

    # Scan successful payments in the last 90 days
    cutoff_90 = now - timedelta(days=90)
    cursor = db.payments.find({"status": "success", "created_at": {"$gte": cutoff_90}})
    payments = await cursor.to_list(1000)

    # Group by customer email
    customer_payments = {}
    for p in payments:
        email = (p.get("email") or "").strip().lower()
        if not email or email in suppressed:
            continue
        if email not in customer_payments:
            customer_payments[email] = []
        customer_payments[email].append(p)

    enqueued_count = 0
    scanned_count = len(customer_payments)

    for email, orders in customer_payments.items():
        # Sort by creation date
        orders.sort(key=lambda x: x.get("created_at") or now)
        first_order = orders[0]
        latest_order = orders[-1]

        first_order_date = first_order.get("created_at") or now
        if first_order_date.tzinfo is None:
            first_order_date = first_order_date.replace(tzinfo=timezone.utc)

        days_since_first = (now - first_order_date).days

        # Aggregate all products purchased across orders
        purchased_slugs = []
        user = await db.users.find_one({"email": email})
        if user and user.get("purchased_products"):
            purchased_slugs.extend(user["purchased_products"])

        for o in orders:
            slug = o.get("product_slug")
            if slug:
                purchased_slugs.append(slug)
            items = o.get("items") or []
            for it in items:
                it_id = it.get("product_id") or it.get("slug")
                if it_id:
                    purchased_slugs.append(it_id)

        # Check subscriber record
        sub = await db.subscribers.find_one({"email": email})
        if sub and not sub.get("is_active", True):
            continue
        unsub_token = sub.get("unsubscribe_token") if sub else ""

        # Recommend cross-sell product
        rec_product = recommend_cross_sell_product(purchased_slugs)
        if not rec_product:
            continue  # Customer already owns all books

        rec_slug = rec_product["slug"]

        # Milestone 1: Day 7 Cross-Sell (Between 6 and 14 days post-purchase)
        if 6 <= days_since_first <= 14:
            log_key = f"cross_sell_d7_{rec_slug}"
            already_sent = await db.marketing_logs.find_one({"email": email, "campaign_id": log_key})
            if not already_sent:
                copy = generate_ai_campaign_copy(
                    product_slug=rec_slug,
                    campaign_type="cross_sell",
                )
                custom_html = (
                    copy["html_body"]
                    .replace("{{ name }}", orders[0].get("name") or "Scholar")
                    .replace("{{ app_url }}", settings.APP_URL)
                    .replace("{{ unsubscribe_token }}", unsub_token)
                )

                await db.email_queue.insert_one({
                    "kind": "marketing",
                    "campaign_id": log_key,
                    "email": email,
                    "name": orders[0].get("name") or "Scholar",
                    "subject": copy["recommended_subject"],
                    "html_body": custom_html,
                    "plain_text": copy.get("plain_text", ""),
                    "unsubscribe_token": unsub_token,
                    "scheduled_at": now,
                    "status": "pending",
                    "retry_count": 0,
                    "created_at": now,
                })

                await db.marketing_logs.insert_one({
                    "campaign_id": log_key,
                    "email": email,
                    "name": orders[0].get("name") or "Scholar",
                    "status": "queued",
                    "milestone": "day_7_cross_sell",
                    "product_slug": rec_slug,
                    "queued_at": now,
                })
                enqueued_count += 1
                continue

        # Milestone 2: Day 21 Cross-Sell (Between 20 and 28 days post-purchase)
        if 20 <= days_since_first <= 28:
            log_key = f"cross_sell_d21_{rec_slug}"
            already_sent = await db.marketing_logs.find_one({"email": email, "campaign_id": log_key})
            if not already_sent:
                copy = generate_ai_campaign_copy(
                    product_slug=rec_slug,
                    campaign_type="direct_response",
                )
                custom_html = (
                    copy["html_body"]
                    .replace("{{ name }}", orders[0].get("name") or "Scholar")
                    .replace("{{ app_url }}", settings.APP_URL)
                    .replace("{{ unsubscribe_token }}", unsub_token)
                )

                await db.email_queue.insert_one({
                    "kind": "marketing",
                    "campaign_id": log_key,
                    "email": email,
                    "name": orders[0].get("name") or "Scholar",
                    "subject": copy["recommended_subject"],
                    "html_body": custom_html,
                    "plain_text": copy.get("plain_text", ""),
                    "unsubscribe_token": unsub_token,
                    "scheduled_at": now,
                    "status": "pending",
                    "retry_count": 0,
                    "created_at": now,
                })

                await db.marketing_logs.insert_one({
                    "campaign_id": log_key,
                    "email": email,
                    "name": orders[0].get("name") or "Scholar",
                    "status": "queued",
                    "milestone": "day_21_cross_sell",
                    "product_slug": rec_slug,
                    "queued_at": now,
                })
                enqueued_count += 1
                continue

        # Milestone 3: Day 60 Win-Back Re-Engagement (> 55 days post-purchase)
        if cfg.get("win_back_enabled", True) and days_since_first >= 55:
            log_key = f"win_back_d60_{rec_slug}"
            already_sent = await db.marketing_logs.find_one({"email": email, "campaign_id": log_key})
            if not already_sent:
                copy = generate_ai_campaign_copy(
                    product_slug=rec_slug,
                    campaign_type="educational_value",
                )
                custom_html = (
                    copy["html_body"]
                    .replace("{{ name }}", orders[0].get("name") or "Friend")
                    .replace("{{ app_url }}", settings.APP_URL)
                    .replace("{{ unsubscribe_token }}", unsub_token)
                )

                await db.email_queue.insert_one({
                    "kind": "marketing",
                    "campaign_id": log_key,
                    "email": email,
                    "name": orders[0].get("name") or "Friend",
                    "subject": copy["recommended_subject"],
                    "html_body": custom_html,
                    "plain_text": copy.get("plain_text", ""),
                    "unsubscribe_token": unsub_token,
                    "scheduled_at": now,
                    "status": "pending",
                    "retry_count": 0,
                    "created_at": now,
                })

                await db.marketing_logs.insert_one({
                    "campaign_id": log_key,
                    "email": email,
                    "name": orders[0].get("name") or "Friend",
                    "status": "queued",
                    "milestone": "day_60_win_back",
                    "product_slug": rec_slug,
                    "queued_at": now,
                })
                enqueued_count += 1

    if enqueued_count > 0:
        print(f"🚀 [Lifecycle Marketing] Scheduled {enqueued_count} personalized cross-sell emails.")
        from ..workers.email_scheduler import process_email_queue
        asyncio.create_task(process_email_queue())

    return {"scanned": scanned_count, "enqueued": enqueued_count}


def start_lifecycle_scheduler():
    """Starts the background lifecycle scheduler."""
    if not getattr(settings, "RUN_SCHEDULERS", True):
        print("⏸️ Lifecycle marketing scheduler disabled (RUN_SCHEDULERS=false)")
        return

    # Run every 6 hours
    scheduler.add_job(
        run_lifecycle_cross_sell_scan,
        IntervalTrigger(hours=6),
        id="lifecycle_cross_sell_scan",
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()
    print("⏰ Lifecycle marketing scheduler started (runs every 6h)")


def stop_lifecycle_scheduler():
    """Stops the lifecycle scheduler on server shutdown."""
    if scheduler.running:
        scheduler.shutdown()
