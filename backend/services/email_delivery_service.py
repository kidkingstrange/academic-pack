"""
Email delivery tracking — read-only queries against the existing
email_queue collection. Built after a systemic ~44% welcome-email
failure rate went undetected for weeks (concurrency bug, fixed
separately) and were only found by manually querying the database.
This exists so that class of problem surfaces on its own next time.

"Welcome" emails are treated as the urgent category throughout — a
failed welcome email blocks a paying customer's actual product access.
A failed sequence/nurture email is a missed marketing touch, not an
access problem, so it's tracked but never given equal visual weight.
"""
from datetime import datetime, timedelta, timezone

WELCOME_KIND = "welcome"


def _kind_label(item: dict) -> str:
    kind = item.get("kind", "sequence")
    if kind == "welcome":
        return "Welcome Email"
    if kind == "affiliate_welcome":
        return "Affiliate Welcome"
    if kind == "affiliate_nudge":
        return "Affiliate Nudge"
    if kind == "checkout_recovery":
        return "Checkout Recovery"
    if kind == "sequence":
        return item.get("subject") or "Sequence Email"
    return kind


def _status_view(item: dict) -> dict:
    """Derives the 4-color status the UI shows, from the raw queue
    fields — on-time (green), sent-after-retries (amber), currently
    retrying (amber), failed (red), not-yet-due/skipped (gray)."""
    status = item.get("status", "pending")
    retry_count = item.get("retry_count", 0) or 0
    if status == "sent":
        return {"tone": "success", "label": "Sent"} if retry_count == 0 else {
            "tone": "warning", "label": f"Sent (after {retry_count} retr{'y' if retry_count == 1 else 'ies'})"
        }
    if status == "retry":
        return {"tone": "warning", "label": f"Retrying ({retry_count}/3)"}
    if status == "failed":
        return {"tone": "danger", "label": "Failed"}
    if status == "skipped":
        return {"tone": "neutral", "label": "Skipped"}
    return {"tone": "neutral", "label": "Scheduled"}


def _serialize(item: dict) -> dict:
    return {
        "id": str(item["_id"]),
        "kind": item.get("kind", "sequence"),
        "label": _kind_label(item),
        "email": item.get("email"),
        "name": item.get("name"),
        "status": item.get("status"),
        "status_view": _status_view(item),
        "retry_count": item.get("retry_count", 0),
        "scheduled_at": item.get("scheduled_at"),
        "sent_at": item.get("sent_at"),
        "last_attempt_at": item.get("last_attempt_at"),
        "error": item.get("error"),
    }


async def get_overview(db) -> dict:
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    sent_24h = await db.email_queue.count_documents({"status": "sent", "sent_at": {"$gte": day_ago}})
    sent_7d = await db.email_queue.count_documents({"status": "sent", "sent_at": {"$gte": week_ago}})
    sent_30d = await db.email_queue.count_documents({"status": "sent", "sent_at": {"$gte": month_ago}})

    failed_total = await db.email_queue.count_documents({"status": "failed"})
    failed_welcome = await db.email_queue.count_documents({"status": "failed", "kind": WELCOME_KIND})
    retrying_total = await db.email_queue.count_documents({"status": "retry"})
    retrying_welcome = await db.email_queue.count_documents({"status": "retry", "kind": WELCOME_KIND})
    pending_total = await db.email_queue.count_documents({"status": "pending"})

    return {
        "sent_24h": sent_24h,
        "sent_7d": sent_7d,
        "sent_30d": sent_30d,
        "failed_total": failed_total,
        "failed_welcome": failed_welcome,
        "retrying_total": retrying_total,
        "retrying_welcome": retrying_welcome,
        "pending_total": pending_total,
    }


async def list_by_status(db, status: str, page: int = 1, limit: int = 50) -> dict:
    """Powers both the Currently Failed and Currently Retrying tables —
    same shape, different status filter. Sorted oldest-first by
    last_attempt_at (falling back to scheduled_at for items that were
    claimed but never actually attempted) so the longest-silently-stuck
    items surface first, same pattern that found the 19 stuck customers."""
    skip = (page - 1) * limit
    query = {"status": status}
    total = await db.email_queue.count_documents(query)
    cursor = db.email_queue.find(query).sort([
        ("last_attempt_at", 1), ("scheduled_at", 1),
    ]).skip(skip).limit(limit)
    items = await cursor.to_list(limit)

    now = datetime.now(timezone.utc)
    out = []
    for item in items:
        row = _serialize(item)
        anchor = item.get("last_attempt_at") or item.get("scheduled_at")
        if anchor:
            if anchor.tzinfo is None:
                anchor = anchor.replace(tzinfo=timezone.utc)
            row["days_stuck"] = round((now - anchor).total_seconds() / 86400, 1)
        else:
            row["days_stuck"] = None
        out.append(row)

    return {"items": out, "total": total, "page": page, "pages": max(1, -(-total // limit))}


async def get_customer_timeline(db, query: str, page: int = 1, limit: int = 50) -> dict:
    """Full chronological email history for a customer, searched by
    email or name. Resolves name matches through `users` first (the
    only collection every checked-out customer has a record in), then
    also matches email_queue.email directly so affiliates/leads who
    never became a `users` record are still found by email."""
    query = (query or "").strip()
    if not query:
        return {"items": [], "total": 0, "page": page, "pages": 1, "matched_emails": []}

    candidate_emails = set()
    async for u in db.users.find(
        {"$or": [{"name": {"$regex": query, "$options": "i"}}, {"email": {"$regex": query, "$options": "i"}}]},
        {"email": 1},
    ).limit(25):
        if u.get("email"):
            candidate_emails.add(u["email"])

    email_filter = {"$or": [{"email": {"$regex": query, "$options": "i"}}]}
    if candidate_emails:
        email_filter["$or"].append({"email": {"$in": list(candidate_emails)}})

    skip = (page - 1) * limit
    total = await db.email_queue.count_documents(email_filter)
    cursor = db.email_queue.find(email_filter).sort([
        ("scheduled_at", 1),
    ]).skip(skip).limit(limit)
    items = await cursor.to_list(limit)

    return {
        "items": [_serialize(i) for i in items],
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),
        "matched_emails": sorted(candidate_emails) if not query.count("@") else [],
    }
