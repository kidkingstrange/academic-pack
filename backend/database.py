"""
MongoDB async connection using Motor.
Collections are initialized here and imported throughout the app.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from .config import get_settings

settings = get_settings()

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    """Call on FastAPI startup."""
    global client, db
    try:
        # Added serverSelectionTimeoutMS to fail quickly if DB is not running
        client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=3000)
        db = client[settings.DB_NAME]
        
        # Backfill subscribers missing unsubscribe_token before creating index
        cursor = db.subscribers.find({"unsubscribe_token": {"$exists": False}})
        async for sub in cursor:
            import secrets
            await db.subscribers.update_one(
                {"_id": sub["_id"]},
                {"$set": {"unsubscribe_token": secrets.token_urlsafe(32)}}
            )

        # Ensure indexes
        await db.users.create_index("email", unique=True)
        await db.leads.create_index("email")
        await db.payments.create_index("reference", unique=True)
        await db.subscribers.create_index("email", unique=True)
        await db.subscribers.create_index("unsubscribe_token", unique=True, sparse=True)
        await db.email_queue.create_index([("status", 1), ("scheduled_at", 1)])
        await db.downloads.create_index([("user_id", 1), ("product_id", 1)])
        await db.used_tokens.create_index("jti", unique=True)
        await db.pending_payments.create_index("reference", unique=True)
        await db.users.create_index("library_access_token", unique=True, sparse=True)
        await db.sessions.create_index("session_hash", unique=True)
        await db.survey_responses.create_index("submitted_at")
        print("✅ MongoDB connected")
    except Exception as e:
        print(f"⚠️ Warning: Could not connect to MongoDB ({e}). Running in UI-only mode.")


async def disconnect_db():
    """Call on FastAPI shutdown."""
    global client
    if client:
        client.close()
        print("🔌 MongoDB disconnected")


def get_db():
    """Dependency injection for database."""
    return db
