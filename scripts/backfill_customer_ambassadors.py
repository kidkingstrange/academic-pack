"""
Backfill & Onboarding Script: Converts all past verified paying customers
into VIP Ambassador Affiliates and sends them their custom activation email.
"""
import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import get_settings
from backend.services.affiliate_service import get_or_create_customer_affiliate
from backend.services.email_service import send_email, render_template

async def main():
    send_live = "--send" in sys.argv
    s = get_settings()
    client = AsyncIOMotorClient(s.MONGODB_URL, serverSelectionTimeoutMS=15000)
    db = client[s.DB_NAME]
    
    # 1. Collect all verified customers from users and payments
    customers = {}
    
    async for u in db.users.find({"role": "customer"}):
        email = (u.get("email") or "").lower().strip()
        if email:
            customers[email] = {
                "name": u.get("name") or "Valued Customer",
                "email": email,
            }
            
    async for p in db.payments.find({"status": {"$in": ["completed", "success"]}}):
        email = (p.get("email") or p.get("customer_email") or "").lower().strip()
        if email and email not in customers:
            customers[email] = {
                "name": p.get("name") or p.get("customer_name") or "Valued Customer",
                "email": email,
            }
            
    # 2. Identify customers not yet in affiliates
    existing_affiliates = {}
    async for a in db.affiliates.find({}):
        em = (a.get("email") or "").lower().strip()
        if em:
            existing_affiliates[em] = a
            
    unconverted = [c for em, c in customers.items() if em not in existing_affiliates]
    
    print("=" * 75, flush=True)
    print("CUSTOMER-TO-AFFILIATE VIP AMBASSADOR ONBOARDING", flush=True)
    print("=" * 75, flush=True)
    print(f"Total Unique Verified Customers: {len(customers)}", flush=True)
    print(f"Already Affiliates: {len(customers) - len(unconverted)}", flush=True)
    print(f"Customers to Auto-Provision & Onboard: {len(unconverted)}", flush=True)
    print(f"Mode: {'🚀 LIVE PROVISIONING & SENDING' if send_live else '🔍 DRY RUN (Pass --send to execute)'}", flush=True)
    print("=" * 75, flush=True)
    
    provisioned_count = 0
    sent_count = 0
    failed_count = 0
    
    for idx, cust in enumerate(unconverted, 1):
        email = cust["email"]
        name = cust["name"]
        
        # In live mode, provision the affiliate record
        if send_live:
            aff_doc, was_created = await get_or_create_customer_affiliate(
                db,
                name=name,
                email=email,
            )
            if was_created:
                provisioned_count += 1
        else:
            # Simulated code for dry-run
            aff_doc = {
                "code": "DRYRUN1234",
                "dashboard_token": "dry_run_token",
            }
            provisioned_count += 1
            
        code = aff_doc.get("code")
        token = aff_doc.get("dashboard_token")
        
        referral_link = f"https://edgepack.thescaleconference.com/?ref={code}"
        recruiter_link = f"https://edgepack.thescaleconference.com/affiliate/register?invite={code}"
        dashboard_link = f"{s.APP_URL}/affiliate/dashboard?token={token}" if token else f"{s.APP_URL}/affiliate/dashboard"
        
        context = {
            "name": name,
            "code": code,
            "referral_link": referral_link,
            "recruiter_link": recruiter_link,
            "dashboard_link": dashboard_link,
            "drive_materials_link": s.AFFILIATE_VIDEO_MATERIALS_LINK,
            "whatsapp_group_link": s.WHATSAPP_AFFILIATE_LINK,
            "app_url": s.APP_URL,
            "unsubscribe_token": token or "default",
        }
        
        subject = f"🎁 Special Gift: You've Been Upgraded to an Official VIP Ambassador, {name}!"
        
        try:
            html_body = render_template("customer_vip_ambassador_upgrade.html", context)
        except Exception as e:
            print(f"❌ Template error for {email}: {e}", flush=True)
            failed_count += 1
            continue
            
        print(f"[{idx:02d}/{len(unconverted):02d}] {name} <{email}> | Code: {code}", flush=True)
        
        if send_live:
            success, err = await send_email(email, subject, html_body)
            if success:
                print(f"      ✅ Provisioned & Email Sent", flush=True)
                sent_count += 1
            else:
                print(f"      ❌ Email Delivery Error: {err}", flush=True)
                failed_count += 1
            # Rate limit SMTP sends
            await asyncio.sleep(1.5)
        else:
            sent_count += 1
            
    print("=" * 75, flush=True)
    print(f"Summary: {provisioned_count} provisioned, {sent_count} {'sent' if send_live else 'validated'}, {failed_count} errors", flush=True)
    print("=" * 75, flush=True)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
