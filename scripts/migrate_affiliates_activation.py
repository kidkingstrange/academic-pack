"""
Safe, idempotent migration and backfill script for affiliate account activation.

Purpose:
  1. Inspects all existing affiliate records in db.affiliates.
  2. Scans for duplicate email addresses and flags them for administrator review
     without merging or corrupting records.
  3. For every existing affiliate who has not established a password:
     - Sets account_activated: False
     - Does NOT assign any shared or default password
     - Preserves all existing IDs, referral codes, bank info, stats, and dashboard tokens.
  4. For any affiliate who already has credentials:
     - Preserves credentials and sets account_activated: True if unset.
  5. Safe and idempotent — can be run multiple times without side effects.

Usage:
  # Dry-run mode (default, inspects database and prints summary without making changes):
  python scripts/migrate_affiliates_activation.py

  # Execute migration:
  python scripts/migrate_affiliates_activation.py --execute

  # Rollback migration (removes account_activated field if needed):
  python scripts/migrate_affiliates_activation.py --rollback
"""
import sys
import os
import asyncio
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import connect_db, get_db, disconnect_db
from backend.config import get_settings


async def main():
    settings = get_settings()
    args = set(sys.argv[1:])

    is_execute = "--execute" in args
    is_rollback = "--rollback" in args

    print("=" * 80)
    print("AFFILIATE ACCOUNT ACTIVATION MIGRATION & BACKFILL")
    print(f"Database: {settings.DB_NAME}")
    if is_rollback:
        print("MODE: ROLLBACK (Removing account_activated field)")
    elif is_execute:
        print("MODE: LIVE EXECUTION (Writing backfill changes to MongoDB)")
    else:
        print("MODE: DRY RUN / AUDIT ONLY (Pass --execute to apply changes)")
    print("=" * 80)

    await connect_db()
    db = get_db()
    if db is None:
        print("❌ Error: Could not connect to database. Ensure MongoDB is reachable.")
        return

    # ── 1. Duplicate Email Detection ─────────────────────────────────────────
    print("\n[Step 1/3] Scanning for duplicate email addresses in db.affiliates...")
    email_pipeline = [
        {"$group": {
            "_id": {"$toLower": "$email"},
            "count": {"$sum": 1},
            "codes": {"$push": "$code"},
            "ids": {"$push": "$_id"}
        }},
        {"$match": {"count": {"$gt": 1}}}
    ]
    duplicate_groups = await db.affiliates.aggregate(email_pipeline).to_list(1000)

    if duplicate_groups:
        print(f"⚠️ ATTENTION: Found {len(duplicate_groups)} email(s) with duplicate affiliate records!")
        print("⚠️ These records will NOT be merged automatically. Flagged for administrator review:")
        for group in duplicate_groups:
            print(f"   • Email: {group['_id']} -> {group['count']} records (Codes: {group['codes']})")
    else:
        print("✅ No duplicate email addresses detected. All affiliate emails are unique.")

    # ── 2. Rollback Handler ──────────────────────────────────────────────────
    if is_rollback:
        print("\n[Rollback] Removing account_activated field from all affiliate records...")
        res = await db.affiliates.update_many(
            {"account_activated": {"$exists": True}},
            {"$unset": {
                "account_activated": "",
                "activation_token_hash": "",
                "activation_token_expires_at": "",
                "reset_token_hash": "",
                "reset_token_expires_at": "",
            }}
        )
        print(f"✅ Rollback complete. Updated {res.modified_count} affiliate record(s).")
        await disconnect_db()
        return

    # ── 3. Scan & Backfill Affiliates ────────────────────────────────────────
    print("\n[Step 2/3] Analyzing existing affiliate records...")
    total_affiliates = await db.affiliates.count_documents({})
    print(f"Total affiliates in database: {total_affiliates}")

    cursor = db.affiliates.find({})
    already_active = 0
    already_set_unactivated = 0
    needs_activation_flag = 0
    needs_active_flag = 0

    affiliates_to_update_false = []
    affiliates_to_update_true = []

    async for aff in cursor:
        aff_id = aff["_id"]
        has_pwd = bool(aff.get("password_hash"))
        has_flag = "account_activated" in aff

        if has_pwd:
            if not aff.get("account_activated"):
                needs_active_flag += 1
                affiliates_to_update_true.append(aff_id)
            else:
                already_active += 1
        else:
            if not has_flag:
                needs_activation_flag += 1
                affiliates_to_update_false.append(aff_id)
            else:
                already_set_unactivated += 1

    print("\n[Inventory Breakdown]")
    print(f"  • Already activated (has password & active flag): {already_active}")
    print(f"  • Already tagged unactivated (account_activated=False): {already_set_unactivated}")
    print(f"  • Needs account_activated=True (has password, flag missing): {needs_active_flag}")
    print(f"  • Needs backfill (legacy affiliate, needs account_activated=False): {needs_activation_flag}")

    # ── 4. Execute Changes ───────────────────────────────────────────────────
    print("\n[Step 3/3] Execution Phase...")
    if not is_execute:
        print("ℹ️ DRY RUN COMPLETE: No database records were modified.")
        print(f"ℹ️ Run 'python scripts/migrate_affiliates_activation.py --execute' to backfill {needs_activation_flag + needs_active_flag} record(s).")
    else:
        modified_count = 0
        if affiliates_to_update_false:
            res_false = await db.affiliates.update_many(
                {"_id": {"$in": affiliates_to_update_false}},
                {"$set": {"account_activated": False}}
            )
            modified_count += res_false.modified_count
            print(f"✅ Marked {res_false.modified_count} legacy affiliate(s) as account_activated=False.")

        if affiliates_to_update_true:
            res_true = await db.affiliates.update_many(
                {"_id": {"$in": affiliates_to_update_true}},
                {"$set": {"account_activated": True}}
            )
            modified_count += res_true.modified_count
            print(f"✅ Marked {res_true.modified_count} affiliate(s) with existing passwords as account_activated=True.")

        print(f"\n🎉 Migration finished successfully! Total modified: {modified_count} record(s).")
        print("All affiliate codes, stats, and historical metrics remain 100% intact.")

    await disconnect_db()


if __name__ == "__main__":
    asyncio.run(main())
