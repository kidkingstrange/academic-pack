"""
Blog Community & Reader Engagement Router
Enables readers to:
1. Log in with their email (+ optional name)
2. Leave comments and share what they liked about blog guides
3. Submit and upvote topics they want Scale Group / Itoya David to write on
Supports both MongoDB (production) and file-backed JSON fallback (local/offline).
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId

from ..database import get_db
from ..utils.security import create_access_token, verify_token
from ..utils.rate_limit import get_real_client_ip

router = APIRouter(prefix="/api/blog", tags=["blog-community"])

# File-backed local fallback store
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
COMMUNITY_DATA_FILE = DATA_DIR / "blog_community.json"

DEFAULT_SEED_DATA = {
    "comments": [
        {
            "id": "c-seed-1",
            "slug": "7-study-habits-first-class-nigerian-students",
            "article_title": "7 Study Habits of First-Class Nigerian University Students",
            "author_name": "Chinedu O.",
            "author_email": "chinedu.student@scale.ng",
            "school": "UNILAG",
            "what_liked": "Active Recall & Timed Sessions",
            "content": "Switching from reading 6 hours straight to the 50-minute active recall blocks completely changed my test scores in second semester. I used to blank out in GST exams, but this method forces you to test yourself before the lecturer does.",
            "created_at": "2026-09-20T14:30:00Z",
            "approved": True
        },
        {
            "id": "c-seed-2",
            "slug": "cgpa-calculation-nigerian-university-5-scale",
            "article_title": "How CGPA is Calculated in Nigerian Universities (5.0 Scale)",
            "author_name": "Amina K.",
            "author_email": "amina.k@scale.ng",
            "school": "ABU Zaria",
            "what_liked": "Mathematical Credit Unit Analysis",
            "content": "The explanation of how a single 4-unit course can drag down your entire semester GPA made me drop one unnecessary elective. It was an eye-opener that saved my 200L results.",
            "created_at": "2026-09-22T09:15:00Z",
            "approved": True
        },
        {
            "id": "c-seed-3",
            "slug": "surviving-squatting-university-hostel",
            "article_title": "Surviving Squatting in Nigerian University Hostels",
            "author_name": "Emeka T.",
            "author_email": "emeka.unn@scale.ng",
            "school": "UNN",
            "what_liked": "Hostel Survival & Mental Boundaries",
            "content": "The advice on setting clear boundaries with bunkmates regarding food and light bulbs saved my sanity in Jaja Hall. Extremely practical advice for Nigerian campus realities.",
            "created_at": "2026-09-25T18:40:00Z",
            "approved": True
        }
    ],
    "topics": [
        {
            "id": "t-seed-1",
            "title": "How to handle a final year project supervisor who ghosted your chapter draft",
            "category": "Academics",
            "why_needed": "Final year students are delayed for months because supervisors ghost them after submission, causing extra year fees.",
            "author_name": "Fadekemi B.",
            "author_email": "fadekemi@scale.ng",
            "votes": 47,
            "voters": ["fadekemi@scale.ng"],
            "status": "In Writing",
            "created_at": "2026-09-18T11:00:00Z"
        },
        {
            "id": "t-seed-2",
            "title": "Managing food inflation & off-campus market budgeting on a ₦30,000 allowance",
            "category": "Finances",
            "why_needed": "Prices of garri, rice, and cooking gas have tripled; students need a tactical meal-prep blueprint to avoid surviving on biscuits.",
            "author_name": "Daniel E.",
            "author_email": "daniel.ui@scale.ng",
            "votes": 54,
            "voters": ["daniel.ui@scale.ng"],
            "status": "Planned",
            "created_at": "2026-09-19T16:20:00Z"
        },
        {
            "id": "t-seed-3",
            "title": "Top high-income remote skills a Nigerian student can master in 6 months",
            "category": "Work & School",
            "why_needed": "We need realistic ways to earn foreign currency online without skipping lectures or getting scammed.",
            "author_name": "Tobi M.",
            "author_email": "tobi.m@scale.ng",
            "votes": 38,
            "voters": ["tobi.m@scale.ng"],
            "status": "Planned",
            "created_at": "2026-09-21T10:15:00Z"
        },
        {
            "id": "t-seed-4",
            "title": "How to recover when a lecturer fails your CA test without showing your script",
            "category": "Academics",
            "why_needed": "Departmental politics make it terrifying to ask for CA remarking. We need a safe diplomatic protocol.",
            "author_name": "Blessing I.",
            "author_email": "blessing@scale.ng",
            "votes": 29,
            "voters": ["blessing@scale.ng"],
            "status": "Community Request",
            "created_at": "2026-09-24T13:45:00Z"
        }
    ]
}


def _load_local_data() -> Dict[str, Any]:
    if not COMMUNITY_DATA_FILE.exists():
        _save_local_data(DEFAULT_SEED_DATA)
        return DEFAULT_SEED_DATA
    try:
        with open(COMMUNITY_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_SEED_DATA


def _save_local_data(data: Dict[str, Any]):
    try:
        with open(COMMUNITY_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: Failed to save blog community local data: {e}")


# ── Schemas ──────────────────────────────────────────────────────────────────

class ReaderLoginRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = ""
    school: Optional[str] = ""


class CommentCreateRequest(BaseModel):
    slug: str
    article_title: Optional[str] = "Academic Guide"
    what_liked: str = Field(..., min_length=2, max_length=150)
    content: str = Field(..., min_length=5, max_length=2000)
    email: Optional[EmailStr] = None
    name: Optional[str] = ""
    school: Optional[str] = ""


class TopicCreateRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    category: str = Field("Academics", max_length=50)
    why_needed: str = Field(..., min_length=10, max_length=1000)
    email: Optional[EmailStr] = None
    name: Optional[str] = ""
    school: Optional[str] = ""


# ── Helper to resolve user from Bearer Token or Request Body ─────────────────

def get_optional_reader(request: Request) -> Optional[Dict[str, Any]]:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = verify_token(token)
        if payload and payload.get("email"):
            return {
                "email": payload.get("email"),
                "name": payload.get("name", ""),
                "id": payload.get("sub", "")
            }
    return None


# ── Auth Endpoints ───────────────────────────────────────────────────────────

@router.post("/auth/login")
async def reader_login(body: ReaderLoginRequest, request: Request, db=Depends(get_db)):
    """
    Log in or register reader via email.
    Returns JWT access token and profile.
    Captures user as a lead / subscriber for Scale Group.
    """
    email = body.email.strip().lower()
    name = (body.name or "").strip() or email.split("@")[0].title()
    school = (body.school or "").strip()
    now_iso = datetime.now(timezone.utc).isoformat()
    client_ip = get_real_client_ip(request)

    reader_id = str(uuid.uuid4())

    # If MongoDB is connected, persist to readers & leads
    if db is not None:
        try:
            reader = await db.readers.find_one({"email": email})
            if reader:
                reader_id = str(reader["_id"])
                # update name/school if provided
                update_fields = {"last_login_at": datetime.now(timezone.utc), "last_ip": client_ip}
                if name and not reader.get("name"):
                    update_fields["name"] = name
                if school:
                    update_fields["school"] = school
                await db.readers.update_one({"_id": reader["_id"]}, {"$set": update_fields})
                name = reader.get("name") or name
                school = reader.get("school") or school
            else:
                ins = await db.readers.insert_one({
                    "email": email,
                    "name": name,
                    "school": school,
                    "created_at": datetime.now(timezone.utc),
                    "last_login_at": datetime.now(timezone.utc),
                    "last_ip": client_ip,
                    "is_active": True
                })
                reader_id = str(ins.inserted_id)

            # Record in leads for Scale Group newsletter/marketing
            await db.leads.update_one(
                {"email": email},
                {"$set": {
                    "name": name,
                    "email": email,
                    "source": "blog_reader_login",
                    "school": school,
                    "last_active": datetime.now(timezone.utc)
                }},
                upsert=True
            )
        except Exception as e:
            print(f"MongoDB reader login warning: {e}")

    token = create_access_token({
        "sub": reader_id,
        "email": email,
        "name": name,
        "school": school,
        "role": "reader"
    })

    return {
        "success": True,
        "message": f"Welcome, {name}!",
        "token": token,
        "user": {
            "id": reader_id,
            "email": email,
            "name": name,
            "school": school
        }
    }


@router.get("/auth/me")
async def get_reader_profile(request: Request, db=Depends(get_db)):
    """Verifies reader session and returns profile data."""
    reader = get_optional_reader(request)
    if not reader:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {"success": True, "user": reader}


# ── Comments Endpoints ───────────────────────────────────────────────────────

@router.get("/comments")
async def get_comments(slug: Optional[str] = None, db=Depends(get_db)):
    """
    Returns comments for a specific blog post slug or recent comments across the site.
    """
    results = []

    if db is not None:
        try:
            query = {"approved": True}
            if slug:
                query["slug"] = slug
            cursor = db.blog_comments.find(query).sort("created_at", -1).limit(50)
            async for doc in cursor:
                results.append({
                    "id": str(doc.get("_id", doc.get("id"))),
                    "slug": doc.get("slug"),
                    "article_title": doc.get("article_title"),
                    "author_name": doc.get("author_name"),
                    "author_email": doc.get("author_email"),
                    "school": doc.get("school", ""),
                    "what_liked": doc.get("what_liked"),
                    "content": doc.get("content"),
                    "created_at": doc.get("created_at") if isinstance(doc.get("created_at"), str) else doc.get("created_at").isoformat() if doc.get("created_at") else "",
                })
        except Exception as e:
            print(f"MongoDB comments fetch warning: {e}")

    # Fallback to local data store if DB empty or offline
    if not results:
        local_data = _load_local_data()
        all_comments = local_data.get("comments", [])
        if slug:
            # Also show general/seed comments if none match the specific slug yet
            matched = [c for c in all_comments if c.get("slug") == slug]
            results = matched if matched else [c for c in all_comments if c.get("approved", True)]
        else:
            results = [c for c in all_comments if c.get("approved", True)]

    return {"success": True, "comments": results, "total": len(results)}


@router.post("/comments")
async def post_comment(body: CommentCreateRequest, request: Request, db=Depends(get_db)):
    """
    Post a reader comment on a blog post.
    Accepts user details from Bearer token or from request body.
    """
    reader = get_optional_reader(request)
    email = (reader.get("email") if reader else (body.email or "")).strip().lower()
    name = (reader.get("name") if reader else (body.name or "")).strip() or (email.split("@")[0].title() if email else "Anonymous Reader")
    school = (reader.get("school") if reader else (body.school or "")).strip()

    if not email:
        raise HTTPException(status_code=400, detail="Please provide your email to comment.")

    client_ip = get_real_client_ip(request)
    now_iso = datetime.now(timezone.utc).isoformat()
    comment_id = f"c-{uuid.uuid4().hex[:8]}"

    comment_doc = {
        "id": comment_id,
        "slug": body.slug,
        "article_title": body.article_title or "Campus Guide",
        "author_name": name,
        "author_email": email,
        "school": school,
        "what_liked": body.what_liked.strip(),
        "content": body.content.strip(),
        "created_at": now_iso,
        "ip_address": client_ip,
        "approved": True
    }

    # Save to MongoDB
    if db is not None:
        try:
            ins = await db.blog_comments.insert_one(dict(comment_doc, created_at=datetime.now(timezone.utc)))
            comment_doc["id"] = str(ins.inserted_id)

            # Auto-capture reader as lead
            await db.leads.update_one(
                {"email": email},
                {"$set": {
                    "name": name,
                    "email": email,
                    "source": "blog_comment",
                    "last_comment_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )
        except Exception as e:
            print(f"MongoDB comment save warning: {e}")

    # Also persist to local JSON store
    local_data = _load_local_data()
    local_data.setdefault("comments", []).insert(0, comment_doc)
    _save_local_data(local_data)

    return {
        "success": True,
        "message": "Thank you for sharing what you liked! Your comment is live.",
        "comment": comment_doc
    }


# ── Topic Requests & Upvoting Endpoints ──────────────────────────────────────

@router.get("/topics")
async def get_topics(category: Optional[str] = None, db=Depends(get_db)):
    """Returns requested topics sorted by vote count."""
    results = []

    if db is not None:
        try:
            query = {}
            if category and category != "All":
                query["category"] = category
            cursor = db.blog_topics.find(query).sort("votes", -1).limit(40)
            async for doc in cursor:
                results.append({
                    "id": str(doc.get("_id", doc.get("id"))),
                    "title": doc.get("title"),
                    "category": doc.get("category", "Academics"),
                    "why_needed": doc.get("why_needed"),
                    "author_name": doc.get("author_name"),
                    "votes": doc.get("votes", 1),
                    "status": doc.get("status", "Community Request"),
                    "created_at": doc.get("created_at") if isinstance(doc.get("created_at"), str) else doc.get("created_at").isoformat() if doc.get("created_at") else "",
                })
        except Exception as e:
            print(f"MongoDB topics fetch warning: {e}")

    if not results:
        local_data = _load_local_data()
        topics = local_data.get("topics", [])
        if category and category != "All":
            topics = [t for t in topics if t.get("category") == category]
        topics.sort(key=lambda x: x.get("votes", 0), reverse=True)
        results = topics

    return {"success": True, "topics": results, "total": len(results)}


@router.post("/topics")
async def submit_topic(body: TopicCreateRequest, request: Request, db=Depends(get_db)):
    """Submit a topic suggestion that readers want Scale Group to write on."""
    reader = get_optional_reader(request)
    email = (reader.get("email") if reader else (body.email or "")).strip().lower()
    name = (reader.get("name") if reader else (body.name or "")).strip() or (email.split("@")[0].title() if email else "Anonymous Student")

    if not email:
        raise HTTPException(status_code=400, detail="Please enter your email so we can notify you when this guide is published.")

    topic_id = f"t-{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    client_ip = get_real_client_ip(request)

    topic_doc = {
        "id": topic_id,
        "title": body.title.strip(),
        "category": body.category.strip(),
        "why_needed": body.why_needed.strip(),
        "author_name": name,
        "author_email": email,
        "votes": 1,
        "voters": [email],
        "status": "Community Request",
        "created_at": now_iso,
        "ip_address": client_ip
    }

    if db is not None:
        try:
            ins = await db.blog_topics.insert_one(dict(topic_doc, created_at=datetime.now(timezone.utc)))
            topic_doc["id"] = str(ins.inserted_id)

            await db.leads.update_one(
                {"email": email},
                {"$set": {
                    "name": name,
                    "email": email,
                    "source": "topic_request",
                    "last_topic_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )
        except Exception as e:
            print(f"MongoDB topic save warning: {e}")

    local_data = _load_local_data()
    local_data.setdefault("topics", []).insert(0, topic_doc)
    _save_local_data(local_data)

    return {
        "success": True,
        "message": "Topic submitted! It has been added to our community roadmap.",
        "topic": topic_doc
    }


@router.post("/topics/{topic_id}/vote")
async def vote_topic(topic_id: str, request: Request, db=Depends(get_db)):
    """Upvote a requested topic."""
    reader = get_optional_reader(request)
    client_ip = get_real_client_ip(request)
    voter_key = reader.get("email") if reader else client_ip

    new_votes = 1

    # MongoDB vote update
    if db is not None:
        try:
            try:
                oid = ObjectId(topic_id)
                query = {"_id": oid}
            except Exception:
                query = {"id": topic_id}

            doc = await db.blog_topics.find_one(query)
            if doc:
                voters = doc.get("voters", [])
                if voter_key not in voters:
                    await db.blog_topics.update_one(
                        query,
                        {"$inc": {"votes": 1}, "$push": {"voters": voter_key}}
                    )
                    new_votes = doc.get("votes", 0) + 1
                else:
                    new_votes = doc.get("votes", 1)
        except Exception as e:
            print(f"MongoDB vote update warning: {e}")

    # Local data store vote update
    local_data = _load_local_data()
    for t in local_data.get("topics", []):
        if t.get("id") == topic_id or str(t.get("_id", "")) == topic_id:
            voters = t.setdefault("voters", [])
            if voter_key not in voters:
                t["votes"] = t.get("votes", 0) + 1
                voters.append(voter_key)
            new_votes = t["votes"]
            break
    _save_local_data(local_data)

    return {
        "success": True,
        "votes": new_votes,
        "message": "Vote recorded! Thank you for helping prioritize this topic."
    }
