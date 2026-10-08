"""
Developer CLI Utility: Test and diagnose an individual affiliate account.

Usage:
    # 1. Test existing affiliate by email:
    python scripts/test_affiliate_account.py --email your_email@example.com

    # 2. Test existing affiliate by referral code:
    python scripts/test_affiliate_account.py --code YOUR_CODE

    # 3. Create a temporary test affiliate, simulate clicks, and test sale attribution:
    python scripts/test_affiliate_account.py --create-test --simulate-sale
"""
import sys
import os
import argparse
import asyncio
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import connect_db, get_db, disconnect_db
from backend.config import get_settings
from backend.services.affiliate_service import create_affiliate_record, ensure_affiliate_subaccount
from backend.services.payment_completion import complete_payment
from backend.utils.security import hash_password, create_access_token


async def run_test(args):
    settings = get_settings()
    is_mock = False

    if args.mock:
        from mongomock_motor import AsyncMongoMockClient
        from backend import database
        mock_client = AsyncMongoMockClient()
        db = mock_client[f"test_{settings.DB_NAME}"]
        database.db = db
        is_mock = True
        print("[Notice] Using isolated in-memory test database (mongomock).")
    else:
        await connect_db()
        db = get_db()
        if db is None:
            if args.create_test:
                print(f"[Notice] Local MongoDB at {settings.MONGODB_URL} is offline.")
                print("         Switching to in-memory test database (mongomock) for this test simulation.")
                from mongomock_motor import AsyncMongoMockClient
                from backend import database
                mock_client = AsyncMongoMockClient()
                db = mock_client[f"test_{settings.DB_NAME}"]
                database.db = db
                is_mock = True
            else:
                print(f"❌ Error: Could not connect to MongoDB at {settings.MONGODB_URL}.")
                print("   To inspect an existing live account, ensure your MongoDB server or Atlas cluster is connected.")
                print("   Tip: You can simulate the full affiliate lifecycle in-memory without a running DB daemon:")
                print("        python scripts/test_affiliate_account.py --create-test --simulate-sale")
                return

    affiliate = None

    if args.create_test:
        test_email = f"test_affiliate_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        print(f"\n[1/4] Creating test affiliate account: {test_email}...")
        affiliate = await create_affiliate_record(
            db,
            name="Test Partner",
            email=test_email,
            source="developer_cli_test",
            commission_percent=60.0,
            bank_name="Access Bank",
            account_number="0123456789",
            account_name="Test Partner",
            password_hash=hash_password("TestPassword123!"),
            account_activated=True,
        )
        affiliate = await ensure_affiliate_subaccount(db, affiliate)
        print(f"✅ Created affiliate with code: {affiliate['code']}")

    elif args.email:
        clean_email = args.email.strip().lower()
        print(f"\n[1/4] Looking up affiliate by email: {clean_email}...")
        affiliate = await db.affiliates.find_one({"email": clean_email})
        if not affiliate:
            print(f"❌ Affiliate with email '{clean_email}' not found.")
            await disconnect_db()
            return

    elif args.code:
        clean_code = args.code.strip().upper()
        print(f"\n[1/4] Looking up affiliate by code: {clean_code}...")
        affiliate = await db.affiliates.find_one({"code": clean_code})
        if not affiliate:
            print(f"❌ Affiliate with code '{clean_code}' not found.")
            await disconnect_db()
            return

    else:
        print("❌ Please specify --email <email>, --code <code>, or --create-test.")
        await disconnect_db()
        return

    # Normalize fields
    code = affiliate["code"]
    email = affiliate["email"]
    name = affiliate["name"]
    is_active = affiliate.get("active") is not False
    is_activated = bool(affiliate.get("account_activated") or affiliate.get("password_hash"))
    rate = affiliate.get("commission_percent", settings.DEFAULT_AFFILIATE_COMMISSION_PERCENT)

    print("\n" + "=" * 65)
    print("AFFILIATE ACCOUNT STATUS & HEALTH AUDIT")
    print("=" * 65)
    print(f"• Name:                {name}")
    print(f"• Email:               {email}")
    print(f"• Referral Code:       {code}")
    print(f"• Commission Rate:     {rate}%")
    print(f"• Account Status:      {'✅ Active' if is_active else '❌ Suspended'}")
    print(f"• Password Set:        {'✅ Activated' if is_activated else '⚠️ Not Activated (Password Not Set)'}")
    print(f"• Bank Name:           {affiliate.get('bank_name') or 'Not provided'}")
    print(f"• Bank Code:           {affiliate.get('bank_code') or 'Not resolved'}")
    print(f"• Account Number:      {affiliate.get('account_number') or 'Not provided'}")
    print(f"• Paystack Subaccount: {affiliate.get('subaccount_code') or 'None (Manual Payout Mode)'}")

    # URLs
    base_url = settings.APP_URL.rstrip('/')
    referral_url = f"{base_url}/r/{code}"
    dashboard_url = f"{base_url}/affiliate/dashboard?token={affiliate.get('dashboard_token', '')}"
    login_url = f"{base_url}/affiliate/login"
    print("\n[Direct Portal & Referral Links]:")
    print(f"• Referral URL:        {referral_url}")
    print(f"• Direct Dashboard:    {dashboard_url}")
    print(f"• Portal Login URL:    {login_url}")

    # 2. Test click tracking
    print("\n[2/4] Testing Referral Click Tracking...")
    before_clicks = await db.referral_clicks.count_documents({"affiliate_code": code})
    await db.referral_clicks.insert_one({
        "affiliate_code": code,
        "ip_address": "127.0.0.1",
        "user_agent": "Developer_Test_Runner",
        "referrer": "test",
        "created_at": datetime.now(timezone.utc),
    })
    after_clicks = await db.referral_clicks.count_documents({"affiliate_code": code})
    print(f"✅ Click logged successfully! (Clicks: {before_clicks} -> {after_clicks})")

    # 3. Simulate sale if requested
    if args.simulate_sale:
        print("\n[3/4] Simulating Test Referred Sale (₦5,000)...")
        test_ref = f"CLI-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        buyer_email = f"buyer_{datetime.now().strftime('%H%M%S')}@example.com"
        
        # Insert pending payment
        await db.pending_payments.insert_one({
            "reference": test_ref,
            "email": buyer_email,
            "name": "Test Student Buyer",
            "amount": 5000.0,
            "referred_by": code,
            "created_at": datetime.now(timezone.utc),
        })

        # Complete payment
        comp_res = await complete_payment(
            db,
            reference=test_ref,
            email=buyer_email,
            name="Test Student Buyer",
            amount=5000.0,
            charge_id=f"ch_{test_ref}",
            gateway_response={"status": "success", "channel": "card"},
            completed_via="developer_cli",
            ip_address="127.0.0.1",
            payment_method="paystack",
        )
        print(f"✅ Sale completed! Reference: {test_ref}")
        ref_record = await db.referrals.find_one({"reference": test_ref})
        if ref_record:
            print(f"   • Commission Recorded: ₦{ref_record.get('commission_amount', 0):,.2f}")
            print(f"   • Status:              {ref_record.get('commission_status')}")
            print(f"   • Customer:            {buyer_email}")
        else:
            print("⚠️ Note: Referral record not found.")

    # 4. Summary of lifetime stats
    total_sales = await db.referrals.count_documents({"affiliate_code": code})
    total_rev_pipeline = [
        {"$match": {"affiliate_code": code}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "comm": {"$sum": "$commission_amount"}}}
    ]
    stat_rows = await db.referrals.aggregate(total_rev_pipeline).to_list(1)
    tot_rev = stat_rows[0]["total"] if stat_rows else 0
    tot_comm = stat_rows[0]["comm"] if stat_rows else 0

    print("\n[4/4] Lifetime Performance Summary:")
    print(f"• Total Clicks:        {after_clicks}")
    print(f"• Total Sales:         {total_sales}")
    print(f"• Revenue Driven:      ₦{tot_rev:,.2f}")
    print(f"• Commission Earned:   ₦{tot_comm:,.2f}")
    print("=" * 65 + "\n")

    if not is_mock:
        await disconnect_db()


def main():
    parser = argparse.ArgumentParser(description="Test and diagnose an affiliate account.")
    parser.add_argument("--email", type=str, help="Affiliate email address")
    parser.add_argument("--code", type=str, help="Affiliate referral code")
    parser.add_argument("--create-test", action="store_true", help="Create a brand new test affiliate")
    parser.add_argument("--simulate-sale", action="store_true", help="Simulate a referred purchase")
    parser.add_argument("--mock", action="store_true", help="Force using in-memory mock database")
    args = parser.parse_args()

    asyncio.run(run_test(args))


if __name__ == "__main__":
    main()
