"""
APScheduler job — builds (never sends) a payout batch on the 1st and
15th of each month. Building a batch only reads Mongo + the live
Flutterwave balance-adjacent data; it never calls the Transfers API.
Sending only happens when an admin clicks Approve in the dashboard
(routes/admin_payouts.py -> services/payout_service.send_batch).
"""
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .. import database
from ..config import get_settings
from ..services.email_service import send_email
from ..services.payout_service import build_pending_batch

scheduler = AsyncIOScheduler()
settings = get_settings()


async def run_biweekly_batch_build():
    db = database.get_db()
    if db is None:
        return
    now = datetime.now(timezone.utc)

    # Guard against firing twice on the same calendar day (process
    # restart landing on the 1st/15th, etc.) — one batch per period.
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    existing_today = await db.payout_batches.find_one({"created_at": {"$gte": today_start}})
    if existing_today:
        return

    last_batch = await db.payout_batches.find_one(sort=[("created_at", -1)])
    period_start = last_batch["created_at"] if last_batch else now

    batch = await build_pending_batch(db, period_start=period_start, period_end=now)
    if not batch:
        print("💸 Payout batch build: nothing owed, skipped")
        return

    print(f"💸 Payout batch built: ₦{batch['total_amount']:,.2f} across {len(batch['items'])} affiliates")

    blocked = [i for i in batch["items"] if i["transfer_status"] == "blocked_missing_bank_code"]
    blocked_note = (
        f"<p style='color:#b45309'><strong>{len(blocked)} affiliate(s) are missing verified bank details</strong> "
        f"and will be skipped until they re-verify: {', '.join(i['affiliate_code'] for i in blocked)}</p>"
        if blocked else ""
    )
    html = f"""
    <p>A new affiliate payout batch is ready for review.</p>
    <p><strong>Total:</strong> ₦{batch['total_amount']:,.2f} across {len(batch['items'])} affiliate(s)</p>
    {blocked_note}
    <p>Review and approve it from the admin dashboard's Payouts tab.</p>
    """
    await send_email(settings.ADMIN_EMAIL, "Affiliate payout batch ready for review", html)


def start_payout_scheduler():
    scheduler.add_job(
        run_biweekly_batch_build,
        CronTrigger(day="1,15", hour=6, minute=0),
        id="payout_batch_builder",
        replace_existing=True,
    )
    scheduler.start()
    print("💰 Payout scheduler started")


def stop_payout_scheduler():
    scheduler.shutdown()
