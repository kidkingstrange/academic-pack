import asyncio
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import get_settings
from backend.services.abandoned_recovery_service import (
    backfill_unconverted_leads,
    is_buyer,
    is_unsubscribed,
    send_recovery_email_step,
    mark_transaction_recovered,
)

async def main():
    send_live = "--send" in sys.argv
    s = get_settings()
    client = AsyncIOMotorClient(s.MONGODB_URL, serverSelectionTimeoutMS=10000)
    db = client[s.DB_NAME]
    
    print("=" * 70, flush=True)
    print("ABANDONED CHECKOUT SYNC & RECOVERY DISPATCHER", flush=True)
    print("=" * 70, flush=True)
    
    # 1. Backfill unconverted leads
    backfilled = await backfill_unconverted_leads(db)
    print(f"✅ Backfilled {backfilled} unconverted leads into abandoned_transactions queue", flush=True)
    
    # 2. Pre-fetch buyer emails for instant checks
    paid_emails = {p.get("email", "").strip().lower() for p in await db.payments.find({"status": "success"}, {"email": 1}).to_list(5000)}
    user_buyers = {u.get("email", "").strip().lower() for u in await db.users.find({"purchased_products": {"$exists": True, "$ne": []}}, {"email": 1}).to_list(5000)}
    all_buyers = paid_emails.union(user_buyers)
    
    # 3. Find eligible abandoned checkouts
    now = datetime.now(timezone.utc)
    abandoned_items = await db.abandoned_transactions.find({
        "status": "pending",
    }).to_list(500)
    
    print(f"Total Pending Abandoned Checkouts: {len(abandoned_items)}", flush=True)
    print(f"Mode: {'🚀 LIVE SENDING' if send_live else '🔍 DRY RUN (Pass --send to execute)'}", flush=True)
    print("=" * 70, flush=True)
    
    sent_count = 0
    skipped_count = 0
    failed_count = 0
    
    for idx, tx in enumerate(abandoned_items, 1):
        email = tx.get("email", "").strip().lower()
        name = tx.get("name") or "there"
        ref = tx.get("reference")
        amount = tx.get("amount", 2000)
        currency = tx.get("currency", "NGN")
        
        # Guard: check if customer already bought
        if email in all_buyers:
            print(f"[{idx}/{len(abandoned_items)}] {email} - SKIPPED (Already a buyer)", flush=True)
            await mark_transaction_recovered(db, email=email)
            skipped_count += 1
            continue
            
        if await is_unsubscribed(db, email):
            print(f"[{idx}/{len(abandoned_items)}] {email} - SKIPPED (Unsubscribed)", flush=True)
            skipped_count += 1
            continue
            
        print(f"[{idx}/{len(abandoned_items)}] {name} <{email}> | Ref: {ref} | Amount: {currency} {amount:,.2f}", flush=True)
        
        if send_live:
            success = await send_recovery_email_step(db, tx, step=1)
            if success:
                print("   ✅ Recovery Email Step 1 Sent", flush=True)
                sent_count += 1
            else:
                print("   ❌ Failed to send recovery email", flush=True)
                failed_count += 1
            await asyncio.sleep(1.5)
        else:
            sent_count += 1
            
    print("=" * 70, flush=True)
    print(f"Summary: {sent_count} {'sent' if send_live else 'ready to send'}, {skipped_count} skipped (buyers/unsubs), {failed_count} failed", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    asyncio.run(main())
