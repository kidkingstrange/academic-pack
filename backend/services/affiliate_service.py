"""
Shared affiliate-creation path for both entry points — the admin-created
flow (routes/affiliates.py) and the public self-registration flow
(routes/affiliate_public.py) — so code generation, uniqueness handling,
and the record shape can never silently diverge between the two.

This system tracks money owed; it never moves money. There is no bank
account, Transfers API, or payout batching anywhere in this file.
"""
import random
import secrets
import string
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from ..config import get_settings

settings = get_settings()


def generate_affiliate_code(name: str) -> str:
    base = "".join(ch for ch in name.upper() if ch.isalpha())[:6] or "AFF"
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{base}{suffix}"


async def create_affiliate_record(
    db,
    *,
    name: str,
    email: str,
    source: str,
    code: str = None,
    commission_percent: float = None,
    registration_ip: str = None,
) -> dict:
    """
    Insert a new affiliate. Raises ValueError("duplicate_email") or
    ValueError("duplicate_code") for the caller to translate into the
    right HTTP response — never raises a raw DuplicateKeyError.

    A caller-specified code that collides is a real error (the caller
    asked for that exact code); an auto-generated collision just retries
    with a fresh one.

    dashboard_token is a separate secret from `code` — `code` is public
    (shared in referral links everywhere), so it can never double as a
    login credential for the affiliate's own stats dashboard.
    """
    email = email.lower()
    if await db.affiliates.find_one({"email": email}):
        raise ValueError("duplicate_email")

    now = datetime.now(timezone.utc)
    resolved_code = (code or "").strip().upper() or generate_affiliate_code(name)
    resolved_commission = (
        commission_percent if commission_percent is not None
        else settings.AFFILIATE_DEFAULT_COMMISSION_PERCENT
    )

    doc = {
        "code": resolved_code,
        "name": name,
        "email": email,
        "active": True,
        "source": source,
        "commission_percent": resolved_commission,
        "dashboard_token": secrets.token_urlsafe(24),
        "created_at": now,
    }
    if registration_ip:
        doc["registration_ip"] = registration_ip

    result = None
    for attempt in range(5):
        try:
            result = await db.affiliates.insert_one(doc)
            break
        except DuplicateKeyError:
            # The email check above already ran, so a collision here is
            # almost certainly the code index, not a late email race.
            if code:
                raise ValueError("duplicate_code")
            if attempt == 4:
                raise ValueError("code_generation_failed")
            doc["code"] = generate_affiliate_code(name)
            resolved_code = doc["code"]

    doc["id"] = str(result.inserted_id)
    doc["code"] = resolved_code
    return doc
