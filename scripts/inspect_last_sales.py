import asyncio
import json
from datetime import datetime
from bson import json_util
from backend.config import get_settings
from motor.motor_asyncio import AsyncIOMotorClient

async def run():
    s = get_settings()
    client = AsyncIOMotorClient(s.MONGODB_URL, serverSelectionTimeoutMS=10000)
    db = client[s.DB_NAME]
    
    # Fetch last 7 successful payments
    cursor = db.payments.find({"status": "success"}).sort("created_at", -1).limit(7)
    payments = await cursor.to_list(length=7)
    
    results = []
    for idx, p in enumerate(payments, 1):
        email = p.get("email")
        ref = p.get("reference")
        user_id = p.get("user_id")
        
        user = await db.users.find_one({"_id": user_id}) if user_id else await db.users.find_one({"email": email})
        ref_record = await db.referrals.find_one({"reference": ref})
        
        affiliate = None
        if ref_record and ref_record.get("affiliate_code"):
            affiliate = await db.affiliates.find_one({"code": ref_record["affiliate_code"]})
            
        lead = await db.leads.find_one({"email": email})
        subscriber = await db.subscribers.find_one({"email": email})
        sales_lead = await db.sales_leads.find_one({"$or": [{"lead_email": email}, {"customer_email": email}]})
        
        # Email queue entries
        emails = await db.email_queue.find({"email": email}).to_list(length=50)
        
        # Downloads
        user_obj_id = user.get("_id") if user else None
        downloads = await db.downloads.find({"user_id": user_obj_id}).to_list(length=50) if user_obj_id else []
        
        # Referral clicks if affiliate
        clicks = []
        if ref_record and ref_record.get("affiliate_code"):
            clicks = await db.referral_clicks.find({"affiliate_code": ref_record["affiliate_code"]}).sort("created_at", -1).limit(5).to_list(length=5)
            
        results.append({
            "sale_index": idx,
            "payment": p,
            "user": user,
            "referral": ref_record,
            "affiliate": affiliate,
            "lead": lead,
            "subscriber": subscriber,
            "sales_lead": sales_lead,
            "emails": emails,
            "downloads": downloads,
            "recent_clicks": clicks
        })
        
    with open("last_7_sales_data.json", "w") as f:
        json.dump(json.loads(json_util.dumps(results)), f, indent=2)
    print("SUCCESS: Wrote last_7_sales_data.json")

if __name__ == "__main__":
    asyncio.run(run())
