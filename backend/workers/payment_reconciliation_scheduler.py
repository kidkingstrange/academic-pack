"""
Background Worker: Payment Auto-Reconciliation Scheduler.
Scans flagged payments and pending payments to automatically resolve and fulfill orders
for customers whose payments succeeded on Paystack but may have experienced network
drops, webhook latency, or gateway fee pass-through mismatch.
"""
import asyncio
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..services.paystack import verify_transaction
from ..services.payment_completion import complete_payment, is_valid_paid_amount
from ..workers.email_scheduler import process_email_queue

scheduler = AsyncIOScheduler()


async def auto_reconcile_flagged_payments(db):
    """
    Checks all unresolved flagged payments with Paystack.
    If Paystack reports success and valid paid amount, automatically fulfills the order.
    """
    try:
        cursor = db.flagged_payments.find({"resolved": {"$ne": True}})
        flagged_list = await cursor.to_list(length=100)
        if not flagged_list:
            return 0

        resolved_count = 0
        now = datetime.now(timezone.utc)

        for item in flagged_list:
            ref = item.get("reference")
            if not ref:
                continue

            # Check if payment already recorded
            existing = await db.payments.find_one({"reference": ref, "status": "success"})
            if existing:
                await db.flagged_payments.update_one(
                    {"reference": ref},
                    {"$set": {"resolved": True, "resolved_at": now, "resolved_by": "existing_payment_check"}}
                )
                continue

            try:
                tx = await verify_transaction(ref)
                if tx.get("status") and tx.get("data", {}).get("status") == "success":
                    tx_data = tx["data"]
                    amount_paid = tx_data.get("amount", 0) / 100.0
                    fee_paid = float((tx_data.get("fees") or 0) / 100.0)

                    pending = await db.pending_payments.find_one({"reference": ref})
                    expected = float(pending.get("amount", 0)) if pending else float(item.get("expected_amount", 0))

                    if expected == 0 or is_valid_paid_amount(amount_paid, expected, fee_paid):
                        cust = tx_data.get("customer", {})
                        email = (pending.get("email") if pending else None) or cust.get("email") or item.get("email")
                        name = (pending.get("name") if pending else None) or f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or "Student"

                        if email:
                            await complete_payment(
                                db,
                                reference=ref,
                                email=email,
                                name=name,
                                amount=amount_paid,
                                charge_id=str(tx_data.get("id")),
                                gateway_response=tx_data,
                                completed_via="auto_reconciliation_worker",
                            )
                            await db.flagged_payments.update_one(
                                {"reference": ref},
                                {"$set": {
                                    "resolved": True,
                                    "resolved_at": now,
                                    "resolved_by": "auto_reconciliation_worker",
                                    "resolution_notes": f"Auto-reconciled and fulfilled for {email}",
                                }}
                            )
                            print(f"[AutoReconcile] Successfully reconciled payment {ref} for {email}")
                            resolved_count += 1
            except Exception as item_err:
                print(f"[AutoReconcile] Error checking {ref}: {item_err}")

        if resolved_count > 0:
            asyncio.create_task(process_email_queue())

        return resolved_count
    except Exception as e:
        print(f"[AutoReconcile] Scheduler run error: {e}")
        return 0


async def _run_job():
    from ..database import db
    if db is not None:
        await auto_reconcile_flagged_payments(db)


def start_reconciliation_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            _run_job,
            trigger=IntervalTrigger(minutes=15),
            id="payment_auto_reconciliation_job",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        print("[Schedulers] Payment auto-reconciliation scheduler started (runs every 15m)")


def stop_reconciliation_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("[Schedulers] Payment auto-reconciliation scheduler stopped")
