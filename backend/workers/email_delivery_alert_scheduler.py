"""
Proactive alerting for welcome-email delivery problems.

The 19-customers-stuck incident that motivated the whole Email Delivery
admin feature happened because a systemic failure (SMTP concurrency
bug) silently accumulated for weeks with nobody checking the database.
This job checks on its own, hourly, and emails the admin the moment a
real problem is forming — not after it's already affected dozens of
customers.

Threshold and cooldown are plain constants, not a rules engine, per
spec ("keep this threshold simple and configurable").
"""
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .. import database
from ..services.email_service import send_welcome_failure_alert_email

scheduler = AsyncIOScheduler()

WELCOME_FAILURE_ALERT_THRESHOLD = 3
ALERT_WINDOW_HOURS = 24
ALERT_COOLDOWN_HOURS = 24

_ALERT_STATE_ID = "email_delivery_welcome_failure_alert"


async def run_alert_check():
    db = database.get_db()
    if db is None:
        return
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=ALERT_WINDOW_HOURS)

    failures = await db.email_queue.find({
        "kind": "welcome",
        "status": "failed",
        "last_attempt_at": {"$gte": window_start},
    }).sort("last_attempt_at", 1).to_list(100)

    if len(failures) < WELCOME_FAILURE_ALERT_THRESHOLD:
        return

    # Cooldown — don't re-alert every hour while the problem persists.
    # One alert per ALERT_COOLDOWN_HOURS is enough to "find out within a
    # day," which is the actual goal, without spamming the admin inbox.
    state = await db.system_state.find_one({"_id": _ALERT_STATE_ID})
    if state and state.get("last_alert_sent_at"):
        last_sent = state["last_alert_sent_at"]
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        if (now - last_sent).total_seconds() < ALERT_COOLDOWN_HOURS * 3600:
            return

    success, _ = await send_welcome_failure_alert_email(
        failed_count=len(failures),
        window_hours=ALERT_WINDOW_HOURS,
        failures=[
            {"email": f.get("email"), "name": f.get("name"), "error": f.get("error")}
            for f in failures
        ],
    )

    await db.system_state.update_one(
        {"_id": _ALERT_STATE_ID},
        {"$set": {"last_alert_sent_at": now, "last_alert_failed_count": len(failures), "last_alert_send_success": success}},
        upsert=True,
    )
    print(f"🚨 Welcome-email failure alert: {len(failures)} failures in {ALERT_WINDOW_HOURS}h — alert email sent={success}")


def start_alert_scheduler():
    scheduler.add_job(
        run_alert_check,
        IntervalTrigger(hours=1),
        id="email_delivery_alert_check",
        replace_existing=True,
    )
    scheduler.start()
    print("🚨 Email delivery alert scheduler started")


def stop_alert_scheduler():
    scheduler.shutdown()
