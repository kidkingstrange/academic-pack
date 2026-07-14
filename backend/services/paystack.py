"""
Paystack payment gateway service.
Abstraction layer — swap with Flutterwave/Stripe by swapping this module.
"""
import hashlib
import hmac
import httpx
from typing import Dict, Any
from ..config import get_settings

settings = get_settings()

PAYSTACK_BASE = "https://api.paystack.co"


async def initialize_transaction(email: str, amount_kobo: int, name: str, reference: str) -> Dict[str, Any]:
    """Initialize a Paystack transaction and return authorization_url."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYSTACK_BASE}/transaction/initialize",
            json={
                "email": email,
                "amount": amount_kobo,
                "currency": "NGN",
                "reference": reference,
                "metadata": {
                    "custom_fields": [
                        {"display_name": "Customer Name", "variable_name": "name", "value": name}
                    ]
                },
                "callback_url": f"{settings.APP_URL}/api/payments/verify",
            },
            headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
            timeout=30,
        )
        return resp.json()


async def verify_transaction(reference: str) -> Dict[str, Any]:
    """Verify a Paystack transaction by reference."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PAYSTACK_BASE}/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
            timeout=30,
        )
        return resp.json()


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """
    Verify Paystack webhook HMAC-SHA512 signature.
    Called before processing any webhook event.
    """
    expected = hmac.new(
        settings.PAYSTACK_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def resolve_account_number(account_number: str, bank_code: str) -> Dict[str, Any]:
    """Resolve a NUBAN account number to verify account holder name via Paystack NIBSS API."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PAYSTACK_BASE}/bank/resolve",
            params={"account_number": account_number, "bank_code": bank_code},
            headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
            timeout=15,
        )
        return resp.json()
