"""
Broadcast Script: Sends the Major Platform Upgrades announcement email
(60% Commission + ₦10,000 Milestone Bonus + ₦5,000 Recruiter Bonus)
to all active affiliates in db.affiliates.
"""
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
    affiliates = await db.affiliates.find({"active": True}).to_list(500)
    
    print("=" * 75, flush=True)
    print("AFFILIATE MAJOR UPDATES BROADCAST DISPATCHER", flush=True)
    print("=" * 75, flush=True)
    print(f"Total Active Affiliates: {len(affiliates)}", flush=True)
    print(f"Mode: {'🚀 LIVE BROADCAST SENDING' if send_live else '🔍 DRY RUN (Pass --send to execute)'}", flush=True)
    print("=" * 75, flush=True)
    
    sent_count = 0
    failed_count = 0
    
    for idx, aff in enumerate(affiliates, 1):
        email = aff.get("email")
        name = aff.get("name") or "there"
        code = aff.get("code")
        token = aff.get("dashboard_token")
        
        # Build links
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
        
        subject = f"🚀 Big Update: 60% Commission, ₦10,000 Milestone Bonus & 2-Tier Earnings, {name}!"
        
        try:
            html_body = render_template("affiliate_major_updates_announcement.html", context)
        except Exception as e:
            print(f"❌ Error rendering template for {email}: {e}", flush=True)
            failed_count += 1
            continue
            
        print(f"[{idx:02d}/{len(affiliates):02d}] {name} <{email}> | Code: {code} | Recruiter Link: invite={code}", flush=True)
        
        if send_live:
            success, err = await send_email(email, subject, html_body)
            if success:
                print(f"      ✅ Sent successfully", flush=True)
                sent_count += 1
            else:
                print(f"      ❌ Delivery error: {err}", flush=True)
                failed_count += 1
            # Rate limit to protect SMTP throughput
            await asyncio.sleep(1.5)
        else:
            sent_count += 1
            
    print("=" * 75, flush=True)
    print(f"Broadcast Summary: {sent_count} {'sent successfully' if send_live else 'validated and ready to send'}, {failed_count} errors", flush=True)
    print("=" * 75, flush=True)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
