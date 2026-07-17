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

    downloads = await db.marketing_asset_downloads.find({
        "downloaded_at": {"$lte": cutoff},
        "nudge_sent": {"$ne": True},
    }).to_list(1000)

    video_clicks = await db.marketing_video_clicks.find({
        "clicked_at": {"$lte": cutoff},
        "nudge_sent": {"$ne": True},
    }).to_list(1000)

    codes = list({d["affiliate_code"] for d in downloads} | {v["affiliate_code"] for v in video_clicks})

    # Two batched queries instead of a count_documents + find_one per
    # candidate — previously O(n) round trips for n candidate codes.
    click_counts = {}
    if codes:
        async for row in db.referral_clicks.aggregate([
            {"$match": {"affiliate_code": {"$in": codes}}},
            {"$group": {"_id": "$affiliate_code", "count": {"$sum": 1}}},
        ]):
            click_counts[row["_id"]] = row["count"]

    affiliates_by_code = {}
    if codes:
        async for aff in db.affiliates.find({"code": {"$in": codes}}):
            affiliates_by_code[aff["code"]] = aff

    seen_codes = set()
    queued = 0
    for code in codes:
        if code in seen_codes:
            continue
        seen_codes.add(code)

        if click_counts.get(code, 0) > 0:
            await db.marketing_asset_downloads.update_many(
                {"affiliate_code": code}, {"$set": {"nudge_sent": True}}
            )
            await db.marketing_video_clicks.update_many(
                {"affiliate_code": code}, {"$set": {"nudge_sent": True}}
            )
            continue

        affiliate = affiliates_by_code.get(code)
        if not affiliate:
            await db.marketing_asset_downloads.update_many(
                {"affiliate_code": code}, {"$set": {"nudge_sent": True}}
            )
            await db.marketing_video_clicks.update_many(
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
        await db.marketing_video_clicks.update_many(
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
