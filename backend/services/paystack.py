"""
Paystack payment gateway service.
Provides transaction initialization, verification, recurring charges,
bank account resolution, and transfers.
"""
import httpx
from typing import Dict, Any, List, Optional
from ..config import get_settings

settings = get_settings()
PAYSTACK_API_BASE = "https://api.paystack.co"


def get_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


async def initialize_transaction(
    email: str,
    amount_naira: float,
    reference: str,
    callback_url: str,
    metadata: Optional[Dict[str, Any]] = None,
    channels: Optional[List[str]] = None,
    currency: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Initialize a Paystack payment transaction.
    Returns payload containing authorization_url, access_code, and reference.
    """
    amount_kobo = int(round(amount_naira * 100))
    payload = {
        "email": email.strip().lower(),
        "amount": amount_kobo,
        "reference": reference,
        "callback_url": callback_url,
    }
    if currency:
        payload["currency"] = currency.upper()
    if metadata:
        payload["metadata"] = metadata
    if channels:
        payload["channels"] = channels

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYSTACK_API_BASE}/transaction/initialize",
            headers=get_headers(),
            json=payload,
            timeout=20,
        )
        data = resp.json()
        if not data.get("status"):
            msg = data.get("message") or "Failed to initialize Paystack transaction"
            raise Exception(f"Paystack initialize error: {msg}")
        return data["data"]


async def verify_transaction(reference: str) -> Dict[str, Any]:
    """
    Verify a Paystack transaction by reference.
    Returns full Paystack response dictionary.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PAYSTACK_API_BASE}/transaction/verify/{reference}",
            headers=get_headers(),
            timeout=20,
        )
        return resp.json()


async def charge_authorization(
    authorization_code: str,
    email: str,
    amount_naira: float,
    reference: str,
) -> Dict[str, Any]:
    """
    Charge a saved card authorization code for recurring subscriptions.
    """
    amount_kobo = int(round(amount_naira * 100))
    payload = {
        "authorization_code": authorization_code,
        "email": email.strip().lower(),
        "amount": amount_kobo,
        "reference": reference,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYSTACK_API_BASE}/transaction/charge_authorization",
            headers=get_headers(),
            json=payload,
            timeout=20,
        )
        return resp.json()


async def list_banks(country: str = "nigeria") -> List[Dict[str, Any]]:
    """
    Fetch bank list for country (default: nigeria).
    Returns list of bank dicts with name, code, etc.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PAYSTACK_API_BASE}/bank?country={country}",
            headers=get_headers(),
            timeout=15,
        )
        data = resp.json()
        if not data.get("status"):
            raise Exception(f"Paystack list_banks error: {data.get('message')}")
        return data.get("data", [])


async def resolve_account_number(account_number: str, bank_code: str) -> Dict[str, Any]:
    """
    Resolve NUBAN account number to holder's account name.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PAYSTACK_API_BASE}/bank/resolve?account_number={account_number}&bank_code={bank_code}",
            headers=get_headers(),
            timeout=15,
        )
        return resp.json()


async def create_transfer_recipient(
    name: str,
    account_number: str,
    bank_code: str,
) -> Dict[str, Any]:
    """
    Register a transfer recipient for automated payouts.
    Returns Paystack recipient creation response dict.
    """
    payload = {
        "type": "nuban",
        "name": name.strip(),
        "account_number": account_number.strip(),
        "bank_code": bank_code.strip(),
        "currency": "NGN",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYSTACK_API_BASE}/transferrecipient",
            headers=get_headers(),
            json=payload,
            timeout=15,
        )
        return resp.json()


async def create_transfer(
    bank_code: str,
    account_number: str,
    amount_naira: float,
    reference: str,
    narration: str,
    recipient_name: str = "Affiliate Recipient",
) -> Dict[str, Any]:
    """
    Send money from Paystack NGN balance to a Nigerian bank account.
    First registers recipient, then creates transfer.
    """
    recipient_resp = await create_transfer_recipient(recipient_name, account_number, bank_code)
    if not recipient_resp.get("status"):
        msg = recipient_resp.get("message") or str(recipient_resp)
        return {"status": False, "message": f"Could not register transfer recipient: {msg}"}

    recipient_code = recipient_resp["data"]["recipient_code"]
    amount_kobo = int(round(amount_naira * 100))

    payload = {
        "source": "balance",
        "amount": amount_kobo,
        "recipient": recipient_code,
        "reference": reference,
        "reason": narration,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYSTACK_API_BASE}/transfer",
            headers=get_headers(),
            json=payload,
            timeout=20,
        )
        data = resp.json()
        if data.get("status"):
            # Map data format to consistent structure
            return {
                "status": "success",
                "data": {
                    "id": data["data"].get("id"),
                    "transfer_code": data["data"].get("transfer_code"),
                    "reference": data["data"].get("reference"),
                    "status": data["data"].get("status"),
                },
            }
        return {"status": "failed", "error": {"message": data.get("message") or "Transfer failed"}}


async def get_paystack_balance() -> Dict[str, Any]:
    """
    Check Paystack NGN balance.
    Returns dict with available NGN balance in Naira.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PAYSTACK_API_BASE}/balance",
            headers=get_headers(),
            timeout=15,
        )
        data = resp.json()
        if not data.get("status"):
            return {"status": False, "message": data.get("message"), "data": {"available_balance": 0.0}}

        avail_ngn_kobo = 0
        for item in data.get("data", []):
            if item.get("currency") == "NGN":
                avail_ngn_kobo = item.get("balance", 0)
                break

        return {
            "status": "success",
            "data": {
                "currency": "NGN",
                "available_balance": avail_ngn_kobo / 100.0,
            },
        }
