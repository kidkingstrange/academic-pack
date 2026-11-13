"""
Script to synchronize product records in MongoDB with the canonical PDF files.
Safe to run multiple times (idempotent).
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import connect_db, get_db, disconnect_db
from backend.config import get_settings
from backend.utils.canonical_products import CANONICAL_PRODUCTS, get_canonical_product

async def sync_products():
    print("Connecting to database...")
    await connect_db()
    db = get_db()
    if db is None:
        print("⚠️ Warning: Could not connect to MongoDB. Skipping DB sync (disk files are already synced).")
        return

    now = datetime.now(timezone.utc)
    for p in CANONICAL_PRODUCTS:
        existing = await db.products.find_one({
            "$or": [
                {"order": p["order"]},
                {"title": p["title"]},
                {"file_path": {"$in": p["aliases"]}},
            ]
        })

        if existing:
            update_data = {
                "title": existing.get("title") or p["title"],
                "description": existing.get("description") or p["description"],
                "file_path": p["file_path"],
                "order": p["order"],
                "is_active": True,
                "updated_at": now,
            }
            if p.get("slug"):
                update_data["slug"] = p["slug"]
            if p.get("price_naira") is not None:
                update_data["price_naira"] = p["price_naira"]
            if p.get("price_usd") is not None:
                update_data["price_usd"] = p["price_usd"]

            await db.products.update_one(
                {"_id": existing["_id"]},
                {"$set": update_data}
            )
            print(f"✅ Updated product order {p['order']}: {p['title']} -> {p['file_path']}")
        else:
            ins = await db.products.insert_one({
                "title": p["title"],
                "description": p["description"],
                "file_path": p["file_path"],
                "thumbnail": None,
                "order": p["order"],
                "slug": p.get("slug"),
                "price_naira": p.get("price_naira", 5000),
                "price_usd": p.get("price_usd", 15.0),
                "is_active": True,
                "created_at": now,
            })
            print(f"✅ Inserted new product order {p['order']}: {p['title']} ({ins.inserted_id})")

    await disconnect_db()
    print("Database sync complete.")

if __name__ == "__main__":
    asyncio.run(sync_products())
