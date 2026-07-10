"""
One-time batch: give EVERY customer with a successful payment record a
fresh durable, non-expiring, reusable library-access link, following the
single-device magic-link fix (see backend/main.py's exchange_magic_token
and the "Replace single-device magic links..." commit).

Deliberately queries db.payments directly (status="success") rather than
db.users or db.subscribers, and does NOT require a subscriber record to
exist first — the whole point is catching every successful payment,
including any that fell through an earlier reconciliation gap. Any
payment whose email has no matching db.users record is reported
separately as needing manual review, never silently dropped.

This is NOT wired into the app — it's a manual script, run once, by hand:

    ./venv/bin/python3 scripts/send_durable_link_backfill.py            # dry run (default)
    ./venv/bin/python3 scripts/send_durable_link_backfill.py --send     # actually sends

Idempotent via a dedicated durable_link_update_sent_at field on the user
doc (separate from library_access_update_sent_at, which was a different,
earlier one-time campaign) — safe to re-run for stragglers without
double-sending anyone already handled.
"""
import argparse
import asyncio
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import get_settings
from backend.services.email_service import send_durable_link_update_email

settings = get_settings()

SEND_DELAY_SECONDS = 3  # generous vs. Private Email's rate limit; just being polite


async def build_recipient_list(db):
    seen_emails = set()
    recipients = []
    skipped = []

    async for payment in db.payments.find({"status": "success"}).sort("created_at", 1):
        email = (payment.get("email") or "").lower()
        if not email or email in seen_emails:
            continue
        seen_emails.add(email)

        user = await db.users.find_one({"email": email})
        if not user:
            skipped.append({
                "email": email,
                "reference": payment.get("reference"),
                "reason": "no matching users record",
            })
            continue

        if user.get("durable_link_update_sent_at"):
            continue  # already handled in a prior run of this script

        sub = await db.subscribers.find_one({"email": email})
        purchase_date = payment.get("verified_at") or payment.get("created_at")
        recipients.append({
            "user_id": user["_id"],
            "name": user.get("name") or payment.get("name") or "there",
            "email": email,
            "unsubscribe_token": sub.get("unsubscribe_token", "") if sub else "",
            "payment_reference": payment.get("reference"),
            "purchase_date": purchase_date,
        })
    return recipients, skipped


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="Actually send. Without this flag, only previews.")
    args = parser.parse_args()

    if args.send:
        bad_url = "localhost" in settings.APP_URL or "127.0.0.1" in settings.APP_URL
        if bad_url:
            print(f"\n❌ REFUSING TO SEND: APP_URL is {settings.APP_URL!r} — that's a local address, not production.")
            print("   Every link would be broken for real customers.")
            print("   Override it for this run, e.g.:")
            print("   APP_URL=https://academic-pack.onrender.com ./venv/bin/python3 scripts/send_durable_link_backfill.py --send\n")
            return
        print(f"APP_URL confirmed production: {settings.APP_URL}")

    client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=15000)
    db = client[settings.DB_NAME]
    print(f"Connected to database: {settings.DB_NAME}")

    total_success_payments = await db.payments.count_documents({"status": "success"})
    recipients, skipped = await build_recipient_list(db)

    print(f"\nTotal successful payment records in db.payments: {total_success_payments}")
    print(f"Unique customers to backfill this run: {len(recipients)}")

    if skipped:
        print(f"\n⚠️  {len(skipped)} payment(s) skipped — no matching users record, needs manual review:")
        for s in skipped:
            print(f"   - {s['email']} (ref: {s['reference']}) — {s['reason']}")

    print(f"\n{'SENDING' if args.send else 'DRY RUN'} — {len(recipients)} recipient(s):\n")
    for i, r in enumerate(recipients, 1):
        pdate = r["purchase_date"].strftime("%Y-%m-%d") if r["purchase_date"] else "unknown date"
        print(f"  {i}. {r['name']!r} <{r['email']}>  (purchased {pdate}, ref: {r['payment_reference']})")

    if not args.send:
        print("\nDry run only — no emails sent, no magic links created. Re-run with --send to actually send.")
        client.close()
        return

    print(f"\nSending for real, {SEND_DELAY_SECONDS}s apart...\n")
    sent_log = []
    for r in recipients:
        now = datetime.now(timezone.utc)
        magic_token = secrets.token_urlsafe(32)
        await db.magic_links.insert_one({
            "token": magic_token,
            "user_id": r["user_id"],
            "purpose": "durable_link_backfill",
            "created_at": now,
        })
        success, error = await send_durable_link_update_email(
            r["name"], r["email"], magic_token, r["unsubscribe_token"]
        )
        sent_at = datetime.now(timezone.utc)
        if success:
            await db.users.update_one(
                {"_id": r["user_id"]},
                {"$set": {"durable_link_update_sent_at": sent_at}},
            )
            print(f"  ✅ sent to {r['email']} at {sent_at.isoformat()}")
            sent_log.append({"email": r["email"], "name": r["name"], "sent_at": sent_at.isoformat(), "status": "sent"})
        else:
            print(f"  ❌ FAILED for {r['email']}: {error}")
            sent_log.append({"email": r["email"], "name": r["name"], "sent_at": sent_at.isoformat(), "status": f"failed: {error}"})
        time.sleep(SEND_DELAY_SECONDS)

    client.close()
    print("\nDone.")
    print("\n=== FULL SEND LOG ===")
    for entry in sent_log:
        print(entry)


if __name__ == "__main__":
    asyncio.run(main())
