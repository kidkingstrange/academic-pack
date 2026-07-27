#!/usr/bin/env python3
"""
Subscriber List Loader & Sanitizer
Extracts subscriber list from MongoDB / local DB / CSV file,
deduplicates emails, validates syntax, and filters out unsubscribed users.
"""
import os
import re
import csv
import json
import sqlite3

UNSUBSCRIBED_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "unsubscribed.txt"))
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def get_unsubscribed_list():
    if not os.path.exists(UNSUBSCRIBED_PATH):
        return set()
    with open(UNSUBSCRIBED_PATH, "r", encoding="utf-8") as f:
        return set(line.strip().lower() for line in f if line.strip())

def load_subscribers_from_db():
    """Attempt to load subscribers from MongoDB or fallback to SQLite preorders."""
    subscribers = []
    
    # Try MongoDB first if URL is set
    mongo_url = os.environ.get("MONGODB_URL")
    if mongo_url:
        try:
            from pymongo import MongoClient
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=3000)
            db_name = os.environ.get("DB_NAME", "academic_comeback")
            db = client[db_name]
            
            # Fetch from preorders and users
            preorders = list(db.preorders.find({}, {"email": 1, "name": 1}))
            for p in preorders:
                if p.get("email"):
                    subscribers.append({"email": p.get("email"), "name": p.get("name") or "Valued Member"})
            
            users = list(db.users.find({}, {"email": 1, "name": 1, "full_name": 1}))
            for u in users:
                if u.get("email"):
                    name = u.get("full_name") or u.get("name") or "Valued Member"
                    subscribers.append({"email": u.get("email"), "name": name})
        except Exception as e:
            print(f"[Loader] Note: MongoDB connection skipped ({e}). Trying local database sources.")

    # Try local sqlite if present
    sqlite_paths = ["backend/database.db", "backend/sql_app.db"]
    for path in sqlite_paths:
        if os.path.exists(path):
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("SELECT email, name FROM preorders WHERE email IS NOT NULL")
                rows = cursor.fetchall()
                for email, name in rows:
                    subscribers.append({"email": email, "name": name or "Valued Member"})
                conn.close()
            except Exception as e:
                pass

    # Default fallback mock list if empty (for local testing)
    if not subscribers:
        subscribers = [
            {"email": "daviditoya@gmail.com", "name": "David Itoya"},
            {"email": "itoya@thescaleconference.com", "name": "Scale Team"},
        ]
        
    return subscribers

def get_clean_subscriber_list():
    unsubscribed = get_unsubscribed_list()
    raw_subscribers = load_subscribers_from_db()

    clean_subscribers = []
    seen = set()

    for sub in raw_subscribers:
        raw_email = sub.get("email", "").strip().lower()
        if not raw_email or not EMAIL_REGEX.match(raw_email):
            continue
        if raw_email in unsubscribed:
            continue
        if raw_email in seen:
            continue

        seen.add(raw_email)
        name = sub.get("name", "Friend").strip()
        if not name or name.lower() in ["none", "null", "valued customer"]:
            name = "Friend"

        clean_subscribers.append({
            "email": raw_email,
            "name": name
        })

    return clean_subscribers

if __name__ == "__main__":
    subs = get_clean_subscriber_list()
    print(f"[Loader] Found {len(subs)} valid, non-unsubscribed recipients:")
    for s in subs[:10]:
        print(f" - {s['name']} <{s['email']}>")
