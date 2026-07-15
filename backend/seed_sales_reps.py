import asyncio
import datetime
from backend import database
from backend.utils.security import hash_password

async def main():
    await database.connect_db()
    db = database.get_db()
    
    if db is None:
        print("❌ Could not connect to MongoDB database")
        return
        
    email = "sales@scalegroup.com"
    existing = await db.sales_reps.find_one({"email": email})
    if existing:
        print(f"ℹ️ Sales representative {email} already exists")
    else:
        rep = {
            "name": "Scale Sales Rep",
            "email": email,
            "password_hash": hash_password("password123"),
            "created_at": datetime.datetime.now(datetime.UTC),
            "active": True
        }
        await db.sales_reps.insert_one(rep)
        print(f"✅ Seeded default sales representative: {email} / password123")
        
    await database.disconnect_db()

if __name__ == "__main__":
    asyncio.run(main())
