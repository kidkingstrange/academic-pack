"""
Automated Review Request Scheduler.
Identifies customers who completed payment 5 to 7 days ago and sends them
a secure, tokenized review request with an incentive.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import traceback

from ..config import get_settings
from ..services.email_service import send_email, render_template
from ..utils.review_token import generate_review_token

settings = get_settings()


async def process_review_requests(db) -> int:
    """
    Finds purchases made 5 to 7 days ago with no review requested yet,
    generates secure review tokens, and dispatches the review request email.
    Returns count of review request emails successfully queued/sent.
    """
    now = datetime.now(timezone.utc)
    five_days_ago = now - timedelta(days=5)
    seven_days_ago = now - timedelta(days=7)

    # Find successful payments completed between 5 and 7 days ago
    query = {
        "status": "success",
        "review_request_sent": {"$ne": True},
        "$or": [
            {"verified_at": {"$gte": seven_days_ago, "$lte": five_days_ago}},
            {"created_at": {"$gte": seven_days_ago, "$lte": five_days_ago}},
        ],
    }

    count = 0
    cursor = db.payments.find(query)
    async for payment in cursor:
        email = (payment.get("email") or "").strip().lower()
        name = payment.get("name") or "Student"
        ref = payment.get("reference")

        if not email or not ref:
            continue

        # Check if customer already submitted a review
        existing_review = await db.reviews.find_one({"email": email})
        if existing_review:
            # Mark payment as done so we don't scan it again
            await db.payments.update_one(
                {"_id": payment["_id"]},
                {"$set": {"review_request_sent": True, "review_request_skipped_reason": "already_reviewed"}}
            )
            continue

        # Generate unique signed review token
        token = generate_review_token(reference=ref, email=email, name=name)
        review_url = f"{settings.APP_URL}/review/{token}"

        try:
            html = render_template(
                "review_request.html",
                name=name.split()[0] if name else "Friend",
                review_url=review_url,
                app_url=settings.APP_URL,
            )
            success, err = await send_email(
                email,
                f"How is your study progress going, {name.split()[0] if name else 'Friend'}? (Quick check-in + 20% gift)",
                html,
            )

            if success:
                await db.payments.update_one(
                    {"_id": payment["_id"]},
                    {"$set": {
                        "review_request_sent": True,
                        "review_request_sent_at": now,
                        "review_token": token,
                    }}
                )
                count += 1
                print(f"⭐ Review request email sent to {email} (ref: {ref})")
            else:
                print(f"⚠️ Failed to send review request email to {email}: {err}")
        except Exception as e:
            print(f"❌ Error processing review request for {email}: {e}")

    return count


async def start_review_scheduler(db):
    """
    Continuous background worker that checks once an hour.
    """
    print("🚀 Automated Review Request Scheduler started.")
    while True:
        try:
            await process_review_requests(db)
        except Exception as e:
            print(f"❌ Review scheduler loop error: {e}")
            traceback.print_exc()

        # Check every 1 hour (3600 seconds)
        await asyncio.sleep(3600)
