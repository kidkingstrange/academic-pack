"""
One-time migration script to generate direct library access tokens for existing users.
Optionally resends the welcome email with the direct link if run with the --send flag.

Usage:
  python scripts/migrate_users_library_access.py [--send]
"""
import sys
import os
import asyncio
import secrets
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import connect_db, get_db, disconnect_db
from backend.config import get_settings
from backend.workers.email_scheduler import process_email_queue

async def run_migration():
    settings = get_settings()
    
    # Require production safeguard (unless run locally with explicit confirm)
    send_emails = "--send" in sys.argv
    
    print("=" * 80)
    print("DIRECT ACCESS TOKEN MIGRATION SCRIPT")
    print(f"Mode: {'REAL RUN & SEND' if send_emails else 'DRY RUN / INVENTORY ONLY'}")
    print("=" * 80)

    await connect_db()
    db = get_db()
    if db is None:
        print("❌ Error: Could not connect to MongoDB.")
        return

    # Find users missing library_access_token
    cursor = db.users.find({"library_access_token": {"$exists": False}})
    users_to_migrate = []
    async for u in cursor:
        users_to_migrate.append(u)

    print(f"Found {len(users_to_migrate)} users missing 'library_access_token'.")

    migrated_count = 0
    queued_count = 0

    for user in users_to_migrate:
        user_id = user["_id"]
        email = user["email"]
        name = user["name"]
        
        # Generate new direct library access token
        access_token = secrets.token_urlsafe(32)
        
        if send_emails:
            # 1. Update user record in DB
            await db.users.update_one(
                {"_id": user_id},
                {"$set": {"library_access_token": access_token}}
            )
            migrated_count += 1
            print(f" Migrated user: {name} ({email}) -> Generated token")

            # Find unsubscribe_token if subscriber exists
            sub = await db.subscribers.find_one({"email": email})
            unsub_token = sub.get("unsubscribe_token", "") if sub else ""

            # 2. Queue updated welcome email
            await db.email_queue.insert_one({
                "kind": "welcome",
                "user_id": user_id,
                "email": email,
                "name": name,
                "access_token": access_token,
                "unsubscribe_token": unsub_token,
                "scheduled_at": datetime.now(timezone.utc),
                "status": "pending",
                "retry_count": 0,
                "sent_at": None,
                "error": None,
            })
            queued_count += 1
            print(f"   Queued new welcome email for resend to {email}")
        else:
            # Dry run display
            print(f" [DRY RUN] Would migrate: {name} ({email}) -> Would generate token")

    print("-" * 80)
    print(f"Migration completed successfully.")
    print(f"Total Migrated: {migrated_count}")
    print(f"Total Welcome Emails Queued: {queued_count}")
    print("=" * 80)

    if send_emails and queued_count > 0:
        print("\nAttempting immediate send of queued welcome emails...")
        await process_email_queue()
        print("Initial send execution finished. Any remaining pending/failed emails will be retried by the background scheduler.")

    await disconnect_db()

if __name__ == "__main__":
    asyncio.run(run_migration())
