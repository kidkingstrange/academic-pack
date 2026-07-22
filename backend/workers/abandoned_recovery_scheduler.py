"""
Background Worker: Abandoned Transaction Recovery Scheduler.
Runs periodically via APScheduler to detect abandoned checkouts, sync Paystack transactions,
and send automated 3-step recovery email sequences.
"""
import asyncio
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .. import database
from ..config import get_settings
from ..services.paystack import list_transactions
from ..services import abandoned_recovery_service

scheduler = AsyncIOScheduler()


async def sync_paystack_abandoned_transactions(db):
    """
    Query Paystack List Transactions endpoint for abandoned & failed transactions,
    ensuring any abandoned payment not captured locally is added to recovery queue.
    """
    try:
        res = await list_transactions(status="abandoned", per_page=30)
        data = res.get("data", []) if isinstance(res, dict) else []
        now = datetime.now(timezone.utc)

        for item in data:
            ref = item.get("reference")
            email = item.get("customer", {}).get("email") or item.get("email")
            if not ref or not email:
                continue

            # Check if reference or email already handled
            existing = await db.abandoned_transactions.find_one({"reference": ref})
            if existing:
                continue

            # Check if customer already completed payment or is a buyer
            if await abandoned_recovery_service.is_buyer(db, email):
                continue

            name = item.get("metadata", {}).get("name") or "Student"
            amount = (item.get("amount", 200000) / 100.0)
            currency = item.get("currency", "NGN")

            paid_at_str = item.get("created_at")
            created_dt = now
            if paid_at_str:
                try:
                    created_dt = datetime.fromisoformat(paid_at_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            await db.abandoned_transactions.insert_one({
                "reference": ref,
                "email": email.strip().lower(),
                "name": name,
                "amount": amount,
                "currency": currency,
                "payment_method": "pay_with_bank",
                "created_at": created_dt,
                "updated_at": now,
                "status": "pending",
                "sequence_step": 0,
                "next_email_at": None,
                "last_email_sent_at": None,
                "emails_sent": [],
                "source": "paystack_api_sync",
            })
    except Exception as e:
        print(f"⚠️ Error syncing abandoned transactions from Paystack API: {e}")


async def run_abandoned_recovery_check():
    """
    Periodic job: process abandoned transactions and advance email recovery sequences.
    """
    db = database.get_db()
    if db is None:
        return

    settings = get_settings()
    if not settings.ABANDONED_RECOVERY_ENABLED:
        return

    now = datetime.now(timezone.utc)

    # 1. Sync from Paystack API to catch any offline/direct abandoned checkouts
    await sync_paystack_abandoned_transactions(db)

    # 2. Transition pending checkouts older than ABANDONED_DELAY_MINUTES_1 to active sequence
    cutoff_1 = now - timedelta(minutes=settings.ABANDONED_DELAY_MINUTES_1)
    pending_items = await db.abandoned_transactions.find({
        "status": "pending",
        "created_at": {"$lte": cutoff_1},
    }).to_list(100)

    for tx in pending_items:
        email = tx.get("email")
        if await abandoned_recovery_service.is_buyer(db, email):
            await abandoned_recovery_service.mark_transaction_recovered(db, email=email)
            continue

        if await abandoned_recovery_service.is_unsubscribed(db, email):
            await db.abandoned_transactions.update_one(
                {"_id": tx["_id"]}, {"$set": {"status": "unsubscribed", "updated_at": now}}
            )
            continue

        # Send Step 1 email immediately
        sent = await abandoned_recovery_service.send_recovery_email_step(db, tx, step=1)
        if sent:
            delay_2_mins = settings.ABANDONED_DELAY_MINUTES_2 - settings.ABANDONED_DELAY_MINUTES_1
            next_due = now + timedelta(minutes=max(1, delay_2_mins))
            await db.abandoned_transactions.update_one(
                {"_id": tx["_id"]},
                {
                    "$set": {
                        "status": "sequence_active",
                        "sequence_step": 1,
                        "next_email_at": next_due,
                        "updated_at": now,
                    }
                },
            )

    # 3. Process active sequences due for Step 2 or Step 3
    due_items = await db.abandoned_transactions.find({
        "status": "sequence_active",
        "next_email_at": {"$lte": now},
    }).to_list(100)

    for tx in due_items:
        email = tx.get("email")
        if await abandoned_recovery_service.is_buyer(db, email):
            await abandoned_recovery_service.mark_transaction_recovered(db, email=email)
            continue

        if await abandoned_recovery_service.is_unsubscribed(db, email):
            await db.abandoned_transactions.update_one(
                {"_id": tx["_id"]}, {"$set": {"status": "unsubscribed", "updated_at": now}}
            )
            continue

        current_step = tx.get("sequence_step", 1)

        if current_step == 1:
            # Send Step 2 email
            sent = await abandoned_recovery_service.send_recovery_email_step(db, tx, step=2)
            if sent:
                delay_3_mins = settings.ABANDONED_DELAY_MINUTES_3 - settings.ABANDONED_DELAY_MINUTES_2
                next_due = now + timedelta(minutes=max(1, delay_3_mins))
                await db.abandoned_transactions.update_one(
                    {"_id": tx["_id"]},
                    {
                        "$set": {
                            "sequence_step": 2,
                            "next_email_at": next_due,
                            "updated_at": now,
                        }
                    },
                )
        elif current_step == 2:
            # Send Step 3 email, then schedule Step 4 (7 days after Step 3)
            sent = await abandoned_recovery_service.send_recovery_email_step(db, tx, step=3)
            if sent:
                delay_4_mins = settings.ABANDONED_DELAY_MINUTES_4 - settings.ABANDONED_DELAY_MINUTES_3
                next_due = now + timedelta(minutes=max(1, delay_4_mins))
                await db.abandoned_transactions.update_one(
                    {"_id": tx["_id"]},
                    {
                        "$set": {
                            "sequence_step": 3,
                            "next_email_at": next_due,
                            "updated_at": now,
                        }
                    },
                )
        elif current_step == 3:
            # Send Step 4 email (1-week ₦2,000 / $15 re-open offer)
            sent = await abandoned_recovery_service.send_recovery_email_step(db, tx, step=4)
            if sent:
                await db.abandoned_transactions.update_one(
                    {"_id": tx["_id"]},
                    {
                        "$set": {
                            "status": "completed",
                            "sequence_step": 4,
                            "next_email_at": None,
                            "updated_at": now,
                        }
                    },
                )



def start_abandoned_recovery_scheduler():
    scheduler.add_job(
        run_abandoned_recovery_check,
        IntervalTrigger(minutes=15),
        id="abandoned_recovery_check",
        replace_existing=True,
    )
    scheduler.start()
    print("⏰ Abandoned transaction recovery scheduler started (runs every 15m)")


def stop_abandoned_recovery_scheduler():
    scheduler.shutdown()
