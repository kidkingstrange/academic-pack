"""
Shared affiliate-creation path for both entry points — the admin-created
flow (routes/affiliates.py) and the public self-registration flow
(routes/affiliate_public.py) — so code generation, uniqueness handling,
and the record shape can never silently diverge between the two.
"""
import random
import string
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError


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
    bank_details: dict = None,
    promotion_info: str = None,
    registration_ip: str = None,
) -> dict:
    """
    Insert a new affiliate. Raises ValueError("duplicate_email") or
    ValueError("duplicate_code") for the caller to translate into the
    right HTTP response — never raises a raw DuplicateKeyError.

    A caller-specified code that collides is a real error (the caller
    asked for that exact code); an auto-generated collision just retries
    with a fresh one.
    """
    email = email.lower()
    if await db.affiliates.find_one({"email": email}):
        raise ValueError("duplicate_email")

    now = datetime.now(timezone.utc)
    resolved_code = (code or "").strip().upper() or generate_affiliate_code(name)

    doc = {
        "code": resolved_code,
        "name": name,
        "email": email,
        "active": True,
        "source": source,
        "created_at": now,
    }
    if bank_details:
        doc["bank_account_number"] = bank_details.get("account_number")
        doc["bank_code"] = bank_details.get("bank_code")
        doc["bank_name"] = bank_details.get("bank_name")
    if promotion_info:
        doc["promotion_info"] = promotion_info
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
