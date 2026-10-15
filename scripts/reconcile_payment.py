"""
Payment Reconciliation and Manual Resolution Utility.

Usage:
    # 1. Inspect and resolve a specific payment reference (e.g. customer on WhatsApp)
    python scripts/reconcile_payment.py --ref ACP-4BF85D69CD3E

    # 2. List all unresolved flagged payments
    python scripts/reconcile_payment.py --list-flagged

    # 3. Automatically check and resolve all flagged payments with Paystack
    python scripts/reconcile_payment.py --resolve-all

    # Optional overrides:
    python scripts/reconcile_payment.py --ref ACP-XXXXX --force --email user@example.com --name "Student Name"
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import get_settings
from backend.services.payment_completion import complete_payment, is_valid_paid_amount
from backend.services.paystack import verify_transaction
from backend.workers.email_scheduler import process_email_queue


async def main():
    parser = argparse.ArgumentParser(description="Reconcile and resolve Paystack transactions.")
    parser.add_argument("--ref", type=str, help="Transaction reference to inspect and resolve (e.g. ACP-4BF85D69CD3E)")
    parser.add_argument("--list-flagged", action="store_true", help="List all unresolved flagged payments")
    parser.add_argument("--resolve-all", action="store_true", help="Auto-resolve all flagged payments that succeed on Paystack")
    parser.add_argument("--force", action="store_true", help="Force resolution even if Paystack API call fails (requires --email)")
    parser.add_argument("--email", type=str, help="Customer email override if not found in records")
    parser.add_argument("--name", type=str, default="Student", help="Customer name override")
    parser.add_argument("--mongo-url", type=str, help="MongoDB connection string override")
    parser.add_argument("--paystack-key", type=str, help="Paystack secret key override")

    args = parser.parse_args()

    settings = get_settings()
    if args.paystack_key:
        os.environ["PAYSTACK_SECRET_KEY"] = args.paystack_key
        settings.PAYSTACK_SECRET_KEY = args.paystack_key

    mongo_url = args.mongo_url or settings.MONGODB_URL
    print(f" Connecting to MongoDB at {mongo_url} (db: {settings.DB_NAME})...")
    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=8000)
    db = client[settings.DB_NAME]

    try:
        await client.admin.command("ping")
        print(" Connected to MongoDB successfully.\n")
    except Exception as e:
        print(f" Failed to connect to MongoDB: {e}")
        print("Tip: Provide --mongo-url <connection_string> if running against remote cluster.")
        return

    # ── 1. List flagged payments ──
    if args.list_flagged or (not args.ref and not args.resolve_all):
        flagged_cursor = db.flagged_payments.find({"resolved": {"$ne": True}}).sort("flagged_at", -1)
        flagged_list = await flagged_cursor.to_list(length=100)
        print(f" Found {len(flagged_list)} unresolved flagged payments:")
        for idx, item in enumerate(flagged_list, 1):
            ref = item.get("reference", "N/A")
            reason = item.get("reason", "unknown")
            expected = item.get("expected_amount", 0)
            paid = item.get("amount_paid", 0)
            payload = item.get("payload", {})
            cust_email = payload.get("customer", {}).get("email") or item.get("email") or "unknown"
            flagged_at = item.get("flagged_at")
            print(f"  {idx}. Ref: {ref} | Reason: {reason} | Expected: ₦{expected} | Paid: ₦{paid} | Email: {cust_email} | Time: {flagged_at}")
        print()
        if not args.ref and not args.resolve_all:
            return

    # ── 2. Resolve single reference ──
    if args.ref:
        ref = args.ref.strip()
        print(f" Inspecting reference: {ref}...")

        flagged = await db.flagged_payments.find_one({"reference": ref})
        pending = await db.pending_payments.find_one({"reference": ref})
        existing_payment = await db.payments.find_one({"reference": ref})

        if existing_payment:
            print(f" Payment record already exists in db.payments! Status: {existing_payment.get('status')}")
            user = await db.users.find_one({"email": existing_payment.get("email")})
            if user:
                print(f" User exists: {user.get('email')}, token: {user.get('library_access_token')}")
                print(f" Direct library link: {settings.APP_URL}/library?token={user.get('library_access_token')}")
            return

        gateway_data = {}
        amount_paid = 0.0
        fee_paid = 0.0
        email = args.email or (pending.get("email") if pending else None)
        name = args.name or (pending.get("name") if pending else "Student")

        if flagged and flagged.get("payload"):
            gateway_data = flagged["payload"]
            amount_paid = float(flagged.get("amount_paid") or (gateway_data.get("amount", 0) / 100.0))
            fee_paid = float((gateway_data.get("fees") or 0) / 100.0)
            cust = gateway_data.get("customer", {})
            if not email:
                email = cust.get("email")
            if name == "Student":
                name = f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or name

        # Query Paystack live
        if not args.force:
            print(f" Verifying {ref} with Paystack API...")
            try:
                tx = await verify_transaction(ref)
                if not tx.get("status") or tx.get("data", {}).get("status") != "success":
                    print(f" Paystack did not confirm success: {tx.get('message')}")
                    if not args.force:
                        print("Use --force if you want to complete this order anyway.")
                        return
                else:
                    gateway_data = tx["data"]
                    amount_paid = gateway_data.get("amount", 0) / 100.0
                    fee_paid = float((gateway_data.get("fees") or 0) / 100.0)
                    cust = gateway_data.get("customer", {})
                    if not email:
                        email = cust.get("email")
                    if name == "Student":
                        name = f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or name
                    print(f" Paystack confirmed! Amount: ₦{amount_paid}, Fees: ₦{fee_paid}, Customer: {email}")
            except Exception as e:
                print(f" Paystack API query failed: {e}")
                if not args.force:
                    print("To bypass Paystack check and fulfill immediately, add --force --email <customer_email>")
                    return

        if not email:
            print(" Customer email could not be determined. Please re-run with --email <customer_email>")
            return

        expected_amount = float(pending.get("amount", 0)) if pending else 5000.0
        print(f" Amount verification: Paid=₦{amount_paid}, Expected=₦{expected_amount}, Fee=₦{fee_paid}")
        valid = is_valid_paid_amount(amount_paid, expected_amount, fee_paid)
        if not valid and not args.force:
            print(f" Amount paid does not satisfy expected total. Use --force to override.")
            return

        print(f" Fulfilling order for {email} ({name})...")
        completion = await complete_payment(
            db,
            reference=ref,
            email=email,
            name=name,
            amount=amount_paid,
            charge_id=str(gateway_data.get("id", ref)),
            gateway_response=gateway_data,
            completed_via="cli_reconciliation",
        )

        now = datetime.now(timezone.utc)
        await db.flagged_payments.update_one(
            {"reference": ref},
            {"$set": {
                "resolved": True,
                "resolved_at": now,
                "resolved_by": "cli_reconciliation",
                "resolution_notes": f"Resolved via CLI script for {email}",
            }},
            upsert=True,
        )

        # Trigger email processing
        print(" Triggering email delivery worker...")
        await process_email_queue()

        user = await db.users.find_one({"_id": completion["user_id"]})
        token = user.get("library_access_token") if user else completion.get("magic_token")
        magic_link = f"{settings.APP_URL}/library?token={token}&welcome=1"

        print("\n" + "=" * 60)
        print(" PAYMENT RECONCILED & ORDER FULFILLED SUCCESSFULLY!")
        print(f" Customer Email: {email}")
        print(f" Reference:      {ref}")
        print(f" Access Token:   {token}")
        print(f" Library Link:   {magic_link}")
        print("=" * 60 + "\n")
        print("You can copy and send the link above directly to the student on WhatsApp!")

    # ── 3. Resolve all flagged payments ──
    if args.resolve_all:
        cursor = db.flagged_payments.find({"resolved": {"$ne": True}})
        flagged_list = await cursor.to_list(length=100)
        print(f" Attempting auto-resolution for {len(flagged_list)} flagged payments...")
        resolved_count = 0
        for item in flagged_list:
            ref = item.get("reference")
            if not ref:
                continue
            try:
                tx = await verify_transaction(ref)
                if tx.get("status") and tx.get("data", {}).get("status") == "success":
                    tx_data = tx["data"]
                    amount_paid = tx_data.get("amount", 0) / 100.0
                    fee_paid = float((tx_data.get("fees") or 0) / 100.0)
                    cust = tx_data.get("customer", {})
                    email = cust.get("email")
                    name = f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or "Student"
                    if email:
                        await complete_payment(
                            db,
                            reference=ref,
                            email=email,
                            name=name,
                            amount=amount_paid,
                            charge_id=str(tx_data.get("id")),
                            gateway_response=tx_data,
                            completed_via="auto_batch_reconciliation",
                        )
                        await db.flagged_payments.update_one(
                            {"reference": ref},
                            {"$set": {"resolved": True, "resolved_at": datetime.now(timezone.utc), "resolved_by": "batch_reconciliation"}},
                        )
                        print(f"   Resolved {ref} for {email}")
                        resolved_count += 1
            except Exception as e:
                print(f"  ❌ Error checking {ref}: {e}")

        print(f"\n Finished batch reconciliation. Resolved {resolved_count}/{len(flagged_list)}.")
        if resolved_count > 0:
            await process_email_queue()


if __name__ == "__main__":
    asyncio.run(main())
