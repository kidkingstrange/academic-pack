"""
One-time batch: notify pre-existing customers (who paid before the
"Access Your Library" returning-customer feature existed) with a fresh
magic link, so clicking it sets their localStorage flag and every future
visit shows "Access Your Library" instead of "Get The Package".

This is NOT wired into the app — it's a manual script, run once, by hand:

    ./venv/bin/python3 scripts/send_library_access_update.py            # dry run (default)
    ./venv/bin/python3 scripts/send_library_access_update.py --send     # actually sends

Idempotent: marks each user with library_access_update_sent_at after a
successful send, and skips anyone already marked, so re-running by
accident (or on purpose, for stragglers) never double-sends.
"""
import argparse
import asyncio
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import get_settings
from backend.services.email_service import send_library_access_update_email

settings = get_settings()

SEND_DELAY_SECONDS = 3  # generous vs. Private Email's 500+/hour limit; just being polite


async def build_recipient_list(db):
    recipients = []
    async for user in db.users.find({"role": "customer"}).sort("created_at", 1):
        email = user["email"]
        if user.get("library_access_update_sent_at"):
            continue  # already handled in a prior run
        sub = await db.subscribers.find_one({"email": email})
        payment = await db.payments.find_one({"email": email, "status": "success"})
        if not sub or not payment:
            print(f"⚠️  Skipping {email} — missing subscriber or payment record (not a clean reconciled customer)")
            continue
        recipients.append({
            "user_id": user["_id"],
            "name": user["name"],
            "email": email,
            "unsubscribe_token": sub.get("unsubscribe_token", ""),
            "payment_reference": payment.get("reference"),
        })
    return recipients


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="Actually send. Without this flag, only previews.")
    args = parser.parse_args()

    if args.send:
        bad_url = "localhost" in settings.APP_URL or "127.0.0.1" in settings.APP_URL
        if bad_url:
            print(f"\n❌ REFUSING TO SEND: APP_URL is {settings.APP_URL!r} — that's a local address, not production.")
            print("   Every magic link would be broken for real customers (the exact past bug this guards against).")
            print("   Override it for this run, e.g.:")
            print("   APP_URL=https://academic-pack.onrender.com ./venv/bin/python3 scripts/send_library_access_update.py --send\n")
            return
        print(f"APP_URL confirmed production: {settings.APP_URL}")

    client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=15000)
    db = client[settings.DB_NAME]

    recipients = await build_recipient_list(db)

    print(f"\n{'SENDING' if args.send else 'DRY RUN'} — {len(recipients)} recipient(s):\n")
    for i, r in enumerate(recipients, 1):
        print(f"  {i}. {r['name']!r} <{r['email']}>  (payment ref: {r['payment_reference']})")

    if not args.send:
        print("\nDry run only — no emails sent, no magic links created. Re-run with --send to actually send.")
        client.close()
        return

    print(f"\nSending for real, {SEND_DELAY_SECONDS}s apart...\n")
    now = datetime.now(timezone.utc)
    for r in recipients:
        magic_token = secrets.token_urlsafe(32)
        await db.magic_links.insert_one({
            "token": magic_token,
            "user_id": r["user_id"],
            "purpose": "library_access_update",
            "expires_at": now + timedelta(days=90),
            "used": False,
            "created_at": now,
        })
        success, error = await send_library_access_update_email(
            r["name"], r["email"], magic_token, r["unsubscribe_token"]
        )
        if success:
            await db.users.update_one(
                {"_id": r["user_id"]},
                {"$set": {"library_access_update_sent_at": datetime.now(timezone.utc)}},
            )
            print(f"  ✅ sent to {r['email']}")
        else:
            print(f"  ❌ FAILED for {r['email']}: {error}")
        time.sleep(SEND_DELAY_SECONDS)

    client.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
