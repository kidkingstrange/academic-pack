"""
Review incentive coupon generation and tracking service.
Issues single-use 20% discount codes to reviewers upon verified submission.
"""
import secrets
from datetime import datetime, timezone
from typing import Optional

from ..config import get_settings
from ..services.email_service import send_email, render_template

settings = get_settings()


async def issue_review_coupon(db, email: str, name: str) -> Optional[str]:
    """
    Creates a single-use 20% discount coupon and sends the thank-you email.
    """
    if not email:
        return None

    email = email.strip().lower()
    coupon_code = f"REV20-{secrets.token_hex(3).upper()}"
    now = datetime.now(timezone.utc)

    # Save to coupons collection
    await db.coupons.update_one(
        {"code": coupon_code},
        {
            "$set": {
                "code": coupon_code,
                "discount_percent": 20,
                "used": False,
                "issued_to": email,
                "created_at": now,
                "reason": "customer_review_incentive",
            }
        },
        upsert=True,
    )

    # Deliver thank you email
    try:
        html = render_template(
            "review_thank_you_coupon.html",
            name=name.split()[0] if name else "Friend",
            coupon_code=coupon_code,
            discount_percent=20,
            app_url=settings.APP_URL,
        )
        await send_email(
            email,
            f"🎁 Your 20% Discount Gift is Here, {name.split()[0] if name else 'Friend'}!",
            html,
        )
    except Exception as e:
        print(f"⚠️ Failed to send review coupon email to {email}: {e}")

    return coupon_code
