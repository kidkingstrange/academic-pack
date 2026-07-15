import asyncio
import datetime
from backend import database

async def main():
    await database.connect_db()
    db = database.get_db()
    
    if db is None:
        print("❌ Could not connect to MongoDB database")
        return
        
    # Clean up existing offers
    await db.offers.delete_many({})
    
    offers = [
        {
            "name": "Business Consultation",
            "description": "1-on-1 Business Strategy and Consultation Session",
            "price": 100000,
            "billing_type": "one_time",
            "duration_months": None
        },
        {
            "name": "1-Month Mentorship",
            "description": "Intensive 1-on-1 Academic Mentorship (Billed Monthly)",
            "price": 50000,
            "billing_type": "recurring_monthly",
            "duration_months": 1
        },
        {
            "name": "3-Month Mentorship",
            "description": "Standard 1-on-1 Academic Mentorship (Billed Monthly)",
            "price": 45000,
            "billing_type": "recurring_monthly",
            "duration_months": 3
        },
        {
            "name": "6-Month Mentorship",
            "description": "Long-term 1-on-1 Academic Mentorship (Billed Monthly)",
            "price": 40000,
            "billing_type": "recurring_monthly",
            "duration_months": 6
        },
        {
            "name": "Cohort",
            "description": "Academic Comeback Group Cohort Access",
            "price": 25000,
            "billing_type": "recurring_monthly",
            "duration_months": None
        },
        {
            "name": "Elite VIP",
            "description": "Premium VIP Boardroom Academic Mentorship",
            "price": 75000,
            "billing_type": "recurring_monthly",
            "duration_months": None
        },
        {
            "name": "Retainer",
            "description": "Academic Advisory Retainer Support",
            "price": 60000,
            "billing_type": "recurring_monthly",
            "duration_months": None
        },
        {
            "name": "Recorded Course",
            "description": "Self-paced Recorded Course Library Access",
            "price": 10000,
            "billing_type": "recurring_monthly",
            "duration_months": None
        }
    ]
    
    for offer in offers:
        offer["created_at"] = datetime.datetime.utcnow()
        await db.offers.insert_one(offer)
        print(f"Seeded offer: {offer['name']} (₦{offer['price']:,})")
        
    print("✅ Seeded all offers successfully")
    await database.disconnect_db()

if __name__ == "__main__":
    asyncio.run(main())
