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

CANONICAL_PRODUCTS = [
    {
        "order": 1,
        "title": "Get Good at Hard Things",
        "description": "A system for academic and skill excellence through discipline, mental depth, and deliberate effort.",
        "file_path": "get_good_at_hard_things.pdf",
        "aliases": ["GET GOOD AT HARD THINGS by David Itoya.pdf", "get_good_at_hard_things.pdf"],
    },
    {
        "order": 2,
        "title": "How to Score High in Any Exam",
        "description": "Proven strategies, smart study techniques, and practical exam preparation protocols to achieve top results.",
        "file_path": "how_to_score_high_in_any_exam.pdf",
        "aliases": ["HOW TO PASS ANY EXAM WITH HIGH SCORES.pdf", "how_to_score_high_in_any_exam.pdf"],
    },
    {
        "order": 3,
        "title": "How to Balance Your Academics and Your Business",
        "description": "A practical guide to excelling in school, growing your business, and building the life you want without burnout.",
        "file_path": "balance_academics_and_business.pdf",
        "aliases": ["HOW TO BALANCE YOUR ACADEMICS AND YOUR BUSINESS.pdf", "balance_academics_and_business.pdf"],
    },
    {
        "order": 4,
        "title": "Result-Oriented Learning",
        "description": "Know exactly what to study for exams. Eliminate wasted effort and focus on high-yield topic mastery.",
        "file_path": "results_oriented_learning.pdf",
        "aliases": ["RESULT-ORIENTED LEARNING.pdf", "results_oriented_learning.pdf"],
    },
    {
        "order": 5,
        "title": "30-Day Study Tracker",
        "description": "Daily progress & discipline system to build consistent study habits, track syllabus coverage, and stay accountable.",
        "file_path": "30_day_study_tracker.pdf",
        "aliases": ["30-Day Study Tracker.pdf", "30_day_study_tracker.pdf"],
    },
    {
        "order": 6,
        "title": "Focus Template",
        "description": "Deep work & distraction elimination system to block out digital noise, build focus stamina, and double study output.",
        "file_path": "focus_template.pdf",
        "aliases": ["🎯 Focus Template.pdf", "focus_template.pdf"],
    },
    {
        "order": 7,
        "title": "Exam Survival Guide",
        "description": "High-stakes preparation & tactical performance protocol for final exams, professional certifications, and tests.",
        "file_path": "exam_survival_guide.pdf",
        "aliases": ["🔥 Exam Survival Guide.pdf", "exam_survival_guide.pdf"],
    },
]

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
            await db.products.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "title": existing.get("title") or p["title"],
                        "description": existing.get("description") or p["description"],
                        "file_path": p["file_path"],
                        "order": p["order"],
                        "is_active": True,
                        "updated_at": now,
                    }
                }
            )
            print(f"✅ Updated product order {p['order']}: {p['title']} -> {p['file_path']}")
        else:
            ins = await db.products.insert_one({
                "title": p["title"],
                "description": p["description"],
                "file_path": p["file_path"],
                "thumbnail": None,
                "order": p["order"],
                "is_active": True,
                "created_at": now,
            })
            print(f"✅ Inserted new product order {p['order']}: {p['title']} ({ins.inserted_id})")

    await disconnect_db()
    print("Database sync complete.")

if __name__ == "__main__":
    asyncio.run(sync_products())
