"""
Recovery emails for failed/abandoned checkout attempts — anyone who
started buying (a `leads` record exists) but never completed payment
(`converted` never flipped True). One email, one time, not a sequence —
same "one-shot nudge" pattern as workers/affiliate_nudge_scheduler.py.

Runs every 30 minutes. A lead only becomes eligible once its checkout
attempt has clearly gone cold (past RECOVERY_DELAY_HOURS — long enough
that a real bank transfer would have reflected already) and is still
recent enough to be worth reaching (within RECOVERY_LOOKBACK_DAYS) — so
turning this feature on doesn't suddenly blast every stale lead from
months ago in one go.
"""
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .. import database

scheduler = AsyncIOScheduler()

RECOVERY_DELAY_HOURS = 1
RECOVERY_LOOKBACK_DAYS = 7


async def run_recovery_check():
    db = database.get_db()
    if db is None:
        return
    now = datetime.now(timezone.utc)
    cutoff_recent = now - timedelta(hours=RECOVERY_DELAY_HOURS)
    cutoff_old = now - timedelta(days=RECOVERY_LOOKBACK_DAYS)

    candidates = await db.leads.find({
        "converted": {"$ne": True},
        "recovery_email_sent": {"$ne": True},
        "created_at": {"$gte": cutoff_old, "$lte": cutoff_recent},
    }).to_list(500)

    queued = 0
    for lead in candidates:
        email = lead.get("email")
        if not email:
            continue

        # Belt-and-suspenders check beyond the `converted` flag — in case
        # it was ever missed by some path, never email someone who
        # actually has a successful payment on record.
        already_paid = await db.payments.find_one({"email": email, "status": "success"})
        if already_paid:
            await db.leads.update_one({"_id": lead["_id"]}, {"$set": {"converted": True, "recovery_email_sent": True}})
            continue

        await db.email_queue.insert_one({
            "kind": "checkout_recovery",
            "email": email,
            "name": lead.get("name") or "there",
            "scheduled_at": now,
            "status": "pending",
            "retry_count": 0,
            "sent_at": None,
            "error": None,
        })
        await db.leads.update_one({"_id": lead["_id"]}, {"$set": {"recovery_email_sent": True}})
        queued += 1

    if queued:
        print(f"💌 Queued {queued} checkout recovery email(s)")
        import asyncio
        from .email_scheduler import process_email_queue
        asyncio.create_task(process_email_queue())


def start_recovery_scheduler():
    scheduler.add_job(
        run_recovery_check,
        IntervalTrigger(minutes=30),
        id="checkout_recovery_check",
        replace_existing=True,
    )
    scheduler.start()
    print("💌 Checkout recovery scheduler started")


def stop_recovery_scheduler():
    scheduler.shutdown()
