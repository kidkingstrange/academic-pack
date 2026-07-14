"""
Daily job: nudge affiliates who downloaded a marketing asset but haven't
clicked their own referral link within 3 days. One email, one time —
not a sequence. Reuses the existing email_queue mechanism/scheduler.
"""
import asyncio
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .. import database
from ..config import get_settings

scheduler = AsyncIOScheduler()


async def run_nudge_check():
    db = database.get_db()
    if db is None:
        return
    settings = get_settings()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=3)

    candidates = await db.marketing_asset_downloads.find({
        "downloaded_at": {"$lte": cutoff},
        "nudge_sent": {"$ne": True},
    }).to_list(1000)

    seen_codes = set()
    queued = 0
    for c in candidates:
        code = c["affiliate_code"]
        if code in seen_codes:
            continue
        seen_codes.add(code)

        click_count = await db.referral_clicks.count_documents({"affiliate_code": code})
        if click_count > 0:
            await db.marketing_asset_downloads.update_many(
                {"affiliate_code": code}, {"$set": {"nudge_sent": True}}
            )
            continue

        affiliate = await db.affiliates.find_one({"code": code})
        if not affiliate:
            await db.marketing_asset_downloads.update_many(
                {"affiliate_code": code}, {"$set": {"nudge_sent": True}}
            )
            continue

        referral_link = f"{settings.APP_URL}/r/{code}"
        await db.email_queue.insert_one({
            "kind": "affiliate_nudge",
            "email": affiliate["email"],
            "name": affiliate["name"],
            "referral_link": referral_link,
            "scheduled_at": now,
            "status": "pending",
            "retry_count": 0,
            "sent_at": None,
            "error": None,
        })
        await db.marketing_asset_downloads.update_many(
            {"affiliate_code": code}, {"$set": {"nudge_sent": True}}
        )
        queued += 1

    if queued:
        print(f"📣 Queued {queued} affiliate nudge email(s)")
        from .email_scheduler import process_email_queue
        asyncio.create_task(process_email_queue())


def start_nudge_scheduler():
    scheduler.add_job(
        run_nudge_check,
        CronTrigger(hour=7, minute=15),
        id="affiliate_nudge_check",
        replace_existing=True,
    )
    scheduler.start()
    print("📣 Affiliate nudge scheduler started")


def stop_nudge_scheduler():
    scheduler.shutdown()
