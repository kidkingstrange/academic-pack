"""
Flutterwave V4 payment gateway service.
Replaces paystack.py — uses OAuth 2.0 client_credentials flow.
"""
import time
import uuid
import httpx
from typing import Dict, Any
from ..config import get_settings

settings = get_settings()

FLW_API_BASE = "https://f4bexperience.flutterwave.com"
FLW_AUTH_URL = "https://idp.flutterwave.com/realms/flutterwave/protocol/openid-connect/token"

# ── OAuth token cache ──────────────────────────────────────────────────────────
_flw_token: str = None
_flw_token_expiry: float = 0


async def get_flw_token() -> str:
    """Fetch and cache a Flutterwave OAuth access token."""
    global _flw_token, _flw_token_expiry
    if _flw_token and time.time() < (_flw_token_expiry - 60):
        return _flw_token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            FLW_AUTH_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_id":     settings.FLW_CLIENT_ID,
                "client_secret": settings.FLW_CLIENT_SECRET,
                "grant_type":    "client_credentials",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        _flw_token        = data["access_token"]
        _flw_token_expiry = time.time() + data.get("expires_in", 600)
        print("🔑 Flutterwave token refreshed")
        return _flw_token


async def create_flw_customer(token: str, name: str, email: str) -> str:
    """Create or retrieve a Flutterwave customer. Returns customer_id."""
    parts = name.strip().split(" ", 1)
    first = parts[0]
    last  = parts[1] if len(parts) > 1 else parts[0]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FLW_API_BASE}/customers",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
                "X-Trace-Id":    str(uuid.uuid4()),
            },
            json={"email": email, "name": {"first": first, "last": last}},
            timeout=15,
        )
        data = resp.json()
        if data.get("status") == "success":
            return data["data"]["id"]
            
        # Fallback if customer already exists
        err_type = data.get("error", {}).get("type")
        if err_type == "CUSTOMER_ALREADY_EXISTS" or "already exists" in str(data).lower():
            search_resp = await client.post(
                f"{FLW_API_BASE}/customers/search",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                },
                json={"email": email},
                timeout=15,
            )
            search_data = search_resp.json()
            if search_data.get("status") == "success" and search_data.get("data"):
                customers = search_data["data"]
                if isinstance(customers, list) and len(customers) > 0:
                    return customers[0]["id"]
                elif isinstance(customers, dict) and "id" in customers:
                    return customers["id"]
                    
        raise Exception(f"FLW customer error: {data}")


async def initiate_bank_transfer(
    token: str,
    customer_id: str,
    amount_naira: int,
    reference: str,
    redirect_url: str,
) -> Dict[str, Any]:
    """
    Create a bank-transfer charge.
    Returns the full charge data including virtual account details.
    """
    async with httpx.AsyncClient() as client:
        # Create bank_transfer payment method
        pm_resp = await client.post(
            f"{FLW_API_BASE}/payment-methods",
            headers={
                "Authorization":     f"Bearer {token}",
                "Content-Type":      "application/json",
                "X-Trace-Id":        str(uuid.uuid4()),
                "X-Idempotency-Key": reference + "-pm",
            },
            json={"type": "bank_account"},
            timeout=15,
        )
        pm_data = pm_resp.json()
        if pm_data.get("status") != "success":
            raise Exception(f"FLW payment-method error: {pm_data}")
        payment_method_id = pm_data["data"]["id"]

        # Create charge
        chg_resp = await client.post(
            f"{FLW_API_BASE}/charges",
            headers={
                "Authorization":     f"Bearer {token}",
                "Content-Type":      "application/json",
                "X-Trace-Id":        str(uuid.uuid4()),
                "X-Idempotency-Key": reference,
            },
            json={
                "reference":         reference,
                "currency":          "NGN",
                "amount":            amount_naira,
                "customer_id":       customer_id,
                "payment_method_id": payment_method_id,
                "redirect_url":      redirect_url,
            },
            timeout=15,
        )
        chg_data = chg_resp.json()
        if chg_data.get("status") != "success":
            raise Exception(f"FLW charge error: {chg_data}")
        return chg_data["data"]


async def verify_flw_charge(charge_id: str) -> Dict[str, Any]:
    """Verify a charge by ID. Returns full API response."""
    token = await get_flw_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FLW_API_BASE}/charges/{charge_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        return resp.json()


async def create_virtual_account(
    token: str,
    customer_id: str,
    amount_naira: int,
    reference: str,
    narration: str,
    bank_code: str = None,
) -> Dict[str, Any]:
    """
    Create a dynamic virtual account for bank transfer payment.
    Returns the full data dict with account_number, account_bank_name,
    amount (includes 2% fee), account_expiration_datetime, etc.
    """
    payload = {
        "reference":    reference,
        "customer_id":  customer_id,
        "amount":       amount_naira,
        "currency":     "NGN",
        "account_type": "dynamic",
        "narration":    narration,
    }
    if bank_code:
        payload["bank_code"] = bank_code

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FLW_API_BASE}/virtual-accounts",
            headers={
                "Authorization":     f"Bearer {token}",
                "Content-Type":      "application/json",
                "X-Trace-Id":        str(uuid.uuid4()),
                "X-Idempotency-Key": reference,
            },
            json=payload,
            timeout=20,
        )
        data = resp.json()
        if data.get("status") != "success":
            raise Exception(f"FLW virtual-account error: {data}")
        return data["data"]


async def list_banks(token: str, country: str = "NG") -> list:
    """Bank list for a country — populates the affiliate registration
    form's bank dropdown so payout account details are captured against
    a real bank_code/bank_name pair rather than free-typed text."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FLW_API_BASE}/banks",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Trace-Id":    str(uuid.uuid4()),
            },
            params={"country": country},
            timeout=15,
        )
        data = resp.json()
        if data.get("status") != "success":
            raise Exception(f"FLW banks error: {data}")
        return data.get("data", [])


async def verify_charges_by_reference(reference: str) -> Dict[str, Any]:
    """Verify a virtual account payment by checking charges for its reference. Returns full API response."""
    token = await get_flw_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FLW_API_BASE}/charges?reference={reference}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        return resp.json()

