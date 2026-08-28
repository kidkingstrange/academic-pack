import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import get_settings

async def analyze():
    s = get_settings()
    client = AsyncIOMotorClient(s.MONGODB_URL, serverSelectionTimeoutMS=10000)
    db = client[s.DB_NAME]
    
    # 1. Total leads & conversion rate
    total_leads = await db.leads.count_documents({})
    converted_leads = await db.leads.count_documents({"converted": True})
    unconverted_leads = await db.leads.count_documents({"converted": False})
    
    # 2. Payments breakdown
    total_payments = await db.payments.count_documents({})
    successful_payments = await db.payments.count_documents({"status": "success"})
    
    rev_pipe = [
        {"$match": {"status": "success"}},
        {"$group": {"_id": None, "total_revenue": {"$sum": "$amount"}, "count": {"$sum": 1}}}
    ]
    rev_res = await db.payments.aggregate(rev_pipe).to_list(1)
    total_revenue = rev_res[0]["total_revenue"] if rev_res else 0
    
    # 3. Abandoned & pending
    total_pending = await db.pending_payments.count_documents({})
    total_abandoned = await db.abandoned_transactions.count_documents({})
    recovered_abandoned = await db.abandoned_transactions.count_documents({"recovered": True})
    
    # 4. Affiliates
    total_affiliates = await db.affiliates.count_documents({})
    active_affiliates = await db.affiliates.count_documents({"active": True})
    total_clicks = await db.referral_clicks.count_documents({})
    total_referrals = await db.referrals.count_documents({})
    
    aff_pipe = [
        {"$group": {
            "_id": "$affiliate_code",
            "count": {"$sum": 1},
            "total_comm": {"$sum": "$commission_amount"},
            "total_sales": {"$sum": "$amount"}
        }},
        {"$sort": {"count": -1}}
    ]
    top_affs = await db.referrals.aggregate(aff_pipe).to_list(10)
    
    # 5. Email queue
    total_emails = await db.email_queue.count_documents({})
    sent_emails = await db.email_queue.count_documents({"status": "sent"})
    pending_emails = await db.email_queue.count_documents({"status": "pending"})
    retry_emails = await db.email_queue.count_documents({"status": "retry"})
    failed_emails = await db.email_queue.count_documents({"status": "failed"})
    
    # 6. Subscribers
    subscribers_count = await db.subscribers.count_documents({})
    buyers_count = await db.subscribers.count_documents({"tags": "buyer"})
    
    # 7. Payment Channels
    channel_pipe = [
        {"$match": {"status": "success"}},
        {"$group": {"_id": "$gateway_response.channel", "count": {"$sum": 1}}}
    ]
    channels = await db.payments.aggregate(channel_pipe).to_list(10)
    
    # 8. Failed / Incomplete checkout attempts logs
    # Check pending_payments timestamps & referral counts
    pending_with_affiliate = await db.pending_payments.count_documents({"referred_by": {"$ne": None}})
    
    print("=" * 60)
    print("WEBSITE HISTORICAL METRICS AUDIT")
    print("=" * 60)
    print(f"Total Leads Captured: {total_leads}")
    print(f"Converted Leads: {converted_leads} ({converted_leads/total_leads*100:.1f}%)" if total_leads else "0 leads")
    print(f"Unconverted Leads (Dropoffs at checkout): {unconverted_leads} ({unconverted_leads/total_leads*100:.1f}%)" if total_leads else "")
    print(f"Total Successful Payments: {successful_payments} | Total Revenue: ₦{total_revenue:,.2f}")
    print(f"Pending/Initiated Checkouts in DB: {total_pending} (with affiliate: {pending_with_affiliate})")
    print(f"Tracked Abandoned Transactions: {total_abandoned} | Recovered: {recovered_abandoned}")
    print(f"Total Registered Affiliates: {total_affiliates} (Active: {active_affiliates})")
    print(f"Total Referral Link Clicks: {total_clicks}")
    print(f"Total Referral Sales: {total_referrals}")
    print("\nTop Affiliates by Sales:")
    for a in top_affs:
        print(f"  - {a['_id']}: {a['count']} sales | ₦{a['total_sales']:,.2f} volume | ₦{a['total_comm']:,.2f} commission")
    print(f"\nEmail Infrastructure Status:")
    print(f"  - Total: {total_emails} | Sent: {sent_emails} | Pending: {pending_emails} | Retrying: {retry_emails} | Failed: {failed_emails}")
    print(f"\nPayment Channels Distribution (Successful):")
    for c in channels:
        print(f"  - {c['_id']}: {c['count']}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(analyze())
