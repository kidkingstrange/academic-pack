"""
Meta Conversions API — server-side event sends.

Purchase: fired exactly once per real completed payment, from
complete_payment()'s `claimed` guard (the same atomic-claim check that
already prevents every other one-time side effect — subscriber
creation, welcome email — from running twice for the same reference).
Uses the payment reference as event_id, matching the client-side Pixel
fire in checkout.js (fireVerifiedPurchase), so Meta deduplicates the
two into one true conversion instead of double-counting.

CompleteRegistration: fired once per affiliate self-registration, from
routes/affiliate_public.py right after the record is created. Uses the
affiliate's code as event_id, matching the client-side fire in
affiliate-register.html, for the same dedup reason. Separate pixel from
Purchase (FB_AFFILIATE_PIXEL_ID), since it's tracking a different
funnel entirely.

Both are additive, not a replacement for the client-side fires — a
second, server-side confirmation that can't be affected by ad blockers,
Safari ITP, in-app browsers that mangle scripts, or JS disabled. Both
no-op safely (return {"sent": False, ...}) if their access token isn't
configured, so calling them unconditionally never breaks the calling
flow.
"""
import hashlib
import time

import httpx

from ..config import get_settings

settings = get_settings()

FB_GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


def _hash_field(value: str) -> str:
    """Meta requires PII fields (email, phone, name) SHA-256 hashed,
    lowercased and trimmed first. IP/user-agent are sent in plaintext —
    never hashed."""
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


async def _send_event(
    *,
    pixel_id: str,
    access_token: str,
    event_name: str,
    event_id: str,
    email: str,
    ip_address: str = None,
    custom_data: dict = None,
    test_event_code: str = None,
) -> dict:
    if not access_token:
        return {"sent": False, "reason": f"access token not configured for pixel {pixel_id}"}

    user_data = {"em": [_hash_field(email)]}
    if ip_address:
        user_data["client_ip_address"] = ip_address

    event = {
        "event_name": event_name,
        "event_time": int(time.time()),
        "event_id": event_id,
        "action_source": "website",
        "user_data": user_data,
    }
    if custom_data:
        event["custom_data"] = custom_data

    payload = {"data": [event]}
    if test_event_code:
        payload["test_event_code"] = test_event_code

    url = f"{FB_GRAPH_API_BASE}/{pixel_id}/events"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, params={"access_token": access_token}, json=payload, timeout=10,
            )
            data = resp.json()
            if resp.status_code == 200 and "events_received" in data:
                return {"sent": True, "response": data}
            return {"sent": False, "reason": data}
    except Exception as e:
        return {"sent": False, "reason": str(e)}


async def send_purchase_event(
    *,
    email: str,
    amount,
    reference: str,
    ip_address: str = None,
    test_event_code: str = None,
) -> dict:
    """
    test_event_code routes the event into Meta's Test Events tab instead
    of real conversion reporting — pass it only when manually verifying
    a token/pixel pairing works, never from complete_payment() itself.
    """
    return await _send_event(
        pixel_id=settings.FB_PIXEL_ID,
        access_token=settings.FB_CAPI_ACCESS_TOKEN,
        event_name="Purchase",
        event_id=reference,
        email=email,
        ip_address=ip_address,
        custom_data={"value": float(amount), "currency": "NGN"},
        test_event_code=test_event_code,
    )


async def send_complete_registration_event(
    *,
    email: str,
    code: str,
    ip_address: str = None,
    test_event_code: str = None,
) -> dict:
    """
    test_event_code routes the event into Meta's Test Events tab instead
    of real conversion reporting — pass it only when manually verifying
    a token/pixel pairing works, never from register_affiliate() itself.
    """
    return await _send_event(
        pixel_id=settings.FB_AFFILIATE_PIXEL_ID,
        access_token=settings.FB_AFFILIATE_CAPI_ACCESS_TOKEN,
        event_name="CompleteRegistration",
        event_id=code,
        email=email,
        ip_address=ip_address,
        custom_data={"content_name": "Affiliate Registration"},
        test_event_code=test_event_code,
    )
