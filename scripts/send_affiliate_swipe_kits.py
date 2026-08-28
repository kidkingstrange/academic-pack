import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import get_settings
from backend.services.email_service import send_email, render_template

async def main():
    send_live = "--send" in sys.argv
    s = get_settings()
    client = AsyncIOMotorClient(s.MONGODB_URL, serverSelectionTimeoutMS=10000)
    db = client[s.DB_NAME]
    
    # 1. Find all active affiliates
    affiliates = await db.affiliates.find({"active": True}).to_list(200)
    
    # 2. Get sales count per affiliate
    ref_counts = {}
    async for r in db.referrals.find({}):
        code = r.get("affiliate_code")
        ref_counts[code] = ref_counts.get(code, 0) + 1
        
    inactive_affiliates = []
    for a in affiliates:
        code = a.get("code")
        sales = ref_counts.get(code, 0)
        if sales == 0:
            inactive_affiliates.append(a)
            
    print("=" * 70, flush=True)
    print(f"AFFILIATE SWIPE KIT & 10-SALE BONUS DISPATCHER", flush=True)
    print("=" * 70, flush=True)
    print(f"Total Active Affiliates: {len(affiliates)}", flush=True)
    print(f"Total Inactive Affiliates (0 sales): {len(inactive_affiliates)}", flush=True)
    print(f"Mode: {'🚀 LIVE SENDING' if send_live else '🔍 DRY RUN (Pass --send to execute)'}", flush=True)
    print("=" * 70, flush=True)
    
    sent_count = 0
    failed_count = 0
    
    for idx, aff in enumerate(inactive_affiliates, 1):
        email = aff.get("email")
        name = aff.get("name") or "there"
        code = aff.get("code")
        token = aff.get("dashboard_token")
        
        referral_link = f"https://edgepack.thescaleconference.com/?ref={code}"
        dashboard_link = f"{s.APP_URL}/affiliate/dashboard?token={token}"
        
        context = {
            "name": name,
            "code": code,
            "referral_link": referral_link,
            "dashboard_link": dashboard_link,
            "drive_materials_link": s.AFFILIATE_VIDEO_MATERIALS_LINK,
            "whatsapp_group_link": s.WHATSAPP_AFFILIATE_LINK,
            "app_url": s.APP_URL,
            "unsubscribe_token": token or "default",
        }
        
        subject = f"🚀 ₦10,000 Bonus Challenge + Your Ready-to-Post Marketing Swipe Kit, {name}"
        
        try:
            html_body = render_template("affiliate_swipe_kit_bonus.html", context)
        except Exception as e:
            print(f"❌ Error rendering template for {email}: {e}", flush=True)
            failed_count += 1
            continue
            
        print(f"[{idx}/{len(inactive_affiliates)}] {name} <{email}> (Code: {code})", flush=True)
        
        if send_live:
            success, err = await send_email(email, subject, html_body)
            if success:
                print(f"   ✅ Sent successfully", flush=True)
                sent_count += 1
            else:
                print(f"   ❌ Delivery error: {err}", flush=True)
                failed_count += 1
            # Rate limiting sleep between SMTP emails to avoid connection throttle
            await asyncio.sleep(1.5)
        else:
            sent_count += 1
            
    print("=" * 70, flush=True)
    print(f"Summary: {sent_count} {'sent' if send_live else 'ready to send'}, {failed_count} failed", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    asyncio.run(main())
