"""
Meta Conversions API — server-side Purchase event.

Fired exactly once per real completed payment, from complete_payment()'s
`claimed` guard (the same atomic-claim check that already prevents every
other one-time side effect — subscriber creation, welcome email — from
running twice for the same reference). Uses the payment reference as
event_id, matching the client-side Pixel fire in checkout.js
(fireVerifiedPurchase), so Meta deduplicates the two into one true
conversion instead of double-counting.

This is additive, not a replacement for the client-side fix — it's a
second, server-side confirmation that can't be affected by ad blockers,
Safari ITP, or a customer with JS disabled.

No-ops safely (returns {"sent": False, ...}) if FB_CAPI_ACCESS_TOKEN
isn't configured, so calling this unconditionally never breaks payment
completion.
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


async def send_purchase_event(
    *,
    email: str,
    amount,
    reference: str,
    ip_address: str = None,
) -> dict:
    if not settings.FB_CAPI_ACCESS_TOKEN:
        return {"sent": False, "reason": "FB_CAPI_ACCESS_TOKEN not configured"}

    user_data = {"em": [_hash_field(email)]}
    if ip_address:
        user_data["client_ip_address"] = ip_address

    payload = {
        "data": [{
            "event_name": "Purchase",
            "event_time": int(time.time()),
            "event_id": reference,
            "action_source": "website",
            "user_data": user_data,
            "custom_data": {
                "value": float(amount),
                "currency": "NGN",
            },
        }],
    }

    url = f"{FB_GRAPH_API_BASE}/{settings.FB_PIXEL_ID}/events"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                params={"access_token": settings.FB_CAPI_ACCESS_TOKEN},
                json=payload,
                timeout=10,
            )
            data = resp.json()
            if resp.status_code == 200 and "events_received" in data:
                return {"sent": True, "response": data}
            return {"sent": False, "reason": data}
    except Exception as e:
        return {"sent": False, "reason": str(e)}
