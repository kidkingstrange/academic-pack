"""
MongoDB async connection using Motor.
Collections are initialized here and imported throughout the app.

NOTE: Motor has been deprecated by MongoDB in favor of PyMongo's own native
async API (pymongo.AsyncMongoClient, stable since PyMongo 4.9) and will stop
receiving updates. No immediate action needed, but this whole module is the
migration surface for eventually switching to that instead — Motor's
AsyncIOMotorClient/AsyncIOMotorDatabase API is close enough to PyMongo's
async client that the change should mostly be import lines + a driver-name
audit, not a rewrite of every route.
"""
import asyncio
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

        # Ensure indexes — run concurrently instead of one round trip at a
        # time. ~25 sequential awaits each paying a full network round trip
        # to Atlas measurably added to cold-start time on top of Render's
        # own free-tier sleep/wake delay; index creation on different (and
        # even the same) collections is safe to run concurrently.
        await asyncio.gather(
            db.users.create_index("email", unique=True),
            db.leads.create_index("email"),
            db.payments.create_index("reference", unique=True),
            db.payments.create_index([("email", 1), ("status", 1)]),
            db.payments.create_index("created_at"),
            db.subscribers.create_index("email", unique=True),
            db.subscribers.create_index("unsubscribe_token", unique=True, sparse=True),
            db.email_queue.create_index([("status", 1), ("scheduled_at", 1)]),
            db.email_queue.create_index("subscriber_id"),
            db.email_queue.create_index([("kind", 1), ("status", 1)]),
            db.downloads.create_index([("user_id", 1), ("product_id", 1)]),
            db.used_tokens.create_index("jti", unique=True),
            db.pending_payments.create_index("reference", unique=True),
            db.users.create_index("library_access_token", unique=True, sparse=True),
            db.sessions.create_index("session_hash", unique=True),
            db.affiliates.create_index("code", unique=True),
            db.affiliates.create_index("email", unique=True),
            db.affiliates.create_index("dashboard_token", unique=True),
            db.referral_clicks.create_index([("affiliate_code", 1), ("created_at", -1)]),
            db.referrals.create_index("reference", unique=True),
            db.referrals.create_index([("affiliate_code", 1), ("commission_status", 1)]),
            # affiliate_health_service.py's MAA/retention windows filter
            # referrals by created_at range with no matching index — a full
            # collection scan on every admin Affiliate Health panel load.
            db.referrals.create_index("created_at"),
            db.payout_batches.create_index([("created_at", -1)]),
            db.payout_batches.create_index([("status", 1)]),
            db.settlement_withdrawals.create_index([("created_at", -1)]),
            db.marketing_asset_downloads.create_index([("affiliate_code", 1), ("downloaded_at", -1)]),
            db.marketing_asset_downloads.create_index([("downloaded_at", 1), ("nudge_sent", 1)]),
            db.marketing_video_clicks.create_index([("affiliate_id", 1), ("clicked_at", -1)]),
            db.marketing_video_clicks.create_index([("affiliate_code", 1), ("clicked_at", -1)]),
            db.marketing_video_clicks.create_index([("clicked_at", 1), ("nudge_sent", 1)]),
            # Subscriptions and Sales Team indexes
            db.offers.create_index("name", unique=True),
            db.sales_leads.create_index("generated_link_token", unique=True),
            db.sales_leads.create_index([("sales_rep_id", 1), ("created_at", -1)]),
            db.subscriptions.create_index("next_charge_date"),
            db.subscriptions.create_index("customer_email"),
        )
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
