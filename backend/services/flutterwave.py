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

if settings.APP_ENV == "production":
    FLW_API_BASE = "https://f4bexperience.flutterwave.com"
else:
    FLW_API_BASE = "https://developersandbox-api.flutterwave.com"

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


async def initiate_card_payment(
    token: str,
    customer_id: str,
    amount_naira: int,
    reference: str,
    redirect_url: str,
    card_number: str,
    cvv: str,
    expiry_month: str,
    expiry_year: str,
    cardholder_name: str,
) -> Dict[str, Any]:
    """
    Create a card payment method and initiate a charge.
    Encrypts card parameters using AES-256-GCM as required by V4 Experience.
    """
    encryption_key = settings.FLW_ENCRYPTION_SECRET
    if not encryption_key:
        raise Exception("FLW_ENCRYPTION_SECRET is not configured in settings")

    # Generate 12-char nonce (6 hex bytes)
    nonce = secrets.token_hex(6)

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import base64

    key_bytes = base64.b64decode(encryption_key)
    aesgcm = AESGCM(key_bytes)
    nonce_bytes = nonce.encode('utf-8')

    enc_number = base64.b64encode(aesgcm.encrypt(nonce_bytes, card_number.strip().replace(" ", "").encode('utf-8'), None)).decode('utf-8')
    enc_month = base64.b64encode(aesgcm.encrypt(nonce_bytes, expiry_month.strip().encode('utf-8'), None)).decode('utf-8')
    enc_year = base64.b64encode(aesgcm.encrypt(nonce_bytes, expiry_year.strip().encode('utf-8'), None)).decode('utf-8')
    enc_cvv = base64.b64encode(aesgcm.encrypt(nonce_bytes, cvv.strip().encode('utf-8'), None)).decode('utf-8')

    async with httpx.AsyncClient() as client:
        # Create card payment method
        pm_resp = await client.post(
            f"{FLW_API_BASE}/payment-methods",
            headers={
                "Authorization":     f"Bearer {token}",
                "Content-Type":      "application/json",
                "X-Trace-Id":        str(uuid.uuid4()),
                "X-Idempotency-Key": reference + "-pm-card",
            },
            json={
                "type": "card",
                "card": {
                    "nonce": nonce,
                    "encrypted_card_number": enc_number,
                    "encrypted_expiry_month": enc_month,
                    "encrypted_expiry_year": enc_year,
                    "encrypted_cvv": enc_cvv,
                    "cardholder_name": cardholder_name.strip()
                }
            },
            timeout=15,
        )
        pm_data = pm_resp.json()
        if pm_data.get("status") != "success":
            raise Exception(f"FLW card payment-method error: {pm_data}")
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
            raise Exception(f"FLW card charge error: {chg_data}")
        return chg_data["data"]


async def charge_token(
    token: str,
    card_token: str,
    amount_naira: int,
    email: str,
    reference: str,
) -> Dict[str, Any]:
    """
    Charge a saved card token for recurring billing.
    Uses the V4 Experience production endpoint /tokenized-charges.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FLW_API_BASE}/tokenized-charges",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Trace-Id": str(uuid.uuid4()),
            },
            json={
                "token": card_token,
                "currency": "NGN",
                "amount": amount_naira,
                "email": email.lower(),
                "tx_ref": reference
            },
            timeout=20,
        )
        return resp.json()


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


async def list_banks(country: str = "NG") -> list:
    """List banks for a country. Returns [{id, code, name}, ...]."""
    token = await get_flw_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FLW_API_BASE}/banks?country={country}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        data = resp.json()
        if data.get("status") != "success":
            raise Exception(f"FLW banks list error: {data}")
        return data["data"]


async def resolve_account_number(account_number: str, bank_code: str) -> Dict[str, Any]:
    """
    Resolve a NUBAN account number to its holder's name via Flutterwave's
    own bank-account-lookup endpoint — used instead of introducing a
    second payment provider (Paystack) for this one feature, since this
    whole app already authenticates with Flutterwave everywhere else.

    Confirmed request/response shape both empirically (live sandbox call)
    and against Flutterwave's official docs:
    POST /banks/account-resolve {"currency": "NGN", "account": {"code", "number"}}
    -> {"status": "success", "data": {"bank_code", "account_number", "account_name"}}
    """
    token = await get_flw_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FLW_API_BASE}/banks/account-resolve",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Trace-Id": str(uuid.uuid4()),
            },
            json={"currency": "NGN", "account": {"code": bank_code, "number": account_number}},
            timeout=15,
        )
        return resp.json()


async def get_ngn_balance() -> Dict[str, Any]:
    """
    Read-only check of the NGN payout balance. Safe to call any time —
    doesn't move money. Used before sending a payout batch (confirm
    balance covers the total) and to compute what's available for the
    "withdraw my share" transfer.
    Returns {"status", "message", "data": {"currency", "available_balance"}}.
    """
    token = await get_flw_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FLW_API_BASE}/wallets/balances/NGN",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Trace-Id": str(uuid.uuid4()),
            },
            timeout=15,
        )
        return resp.json()


async def create_transfer_recipient(bank_code: str, account_number: str) -> Dict[str, Any]:
    """
    Register a bank account as a transfer recipient — a real, empirically-
    confirmed prerequisite for create_transfer() below. The "Bank Account
    Transfers" guide's example (bank details embedded directly in the
    transfer request) looked simpler and matched official docs, but the
    live API rejected it with "payment_instruction.recipient_id must not
    be null" on the very first real transfer attempt — this two-step
    flow (register recipient, then reference its id) is what the API
    actually requires.
    """
    token = await get_flw_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FLW_API_BASE}/transfers/recipients",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Trace-Id": str(uuid.uuid4()),
            },
            json={"type": "bank_ngn", "bank": {"account_number": account_number, "code": bank_code}},
            timeout=15,
        )
        return resp.json()


async def create_transfer(
    bank_code: str,
    account_number: str,
    amount_naira: float,
    reference: str,
    narration: str,
) -> Dict[str, Any]:
    """
    Send money from the Flutterwave NGN payout balance to a Nigerian bank
    account — this one actually moves money, unlike every other function
    in this file. Registers a transfer recipient first (see
    create_transfer_recipient() above), then creates the transfer
    referencing that recipient's id — confirmed empirically against the
    live API after the embedded-bank-details approach was rejected.

    reference must be unique per transfer — Flutterwave treats it as an
    idempotency key, so a retried call with the same reference is safe
    (won't double-send).
    """
    token = await get_flw_token()

    recipient_resp = await create_transfer_recipient(bank_code, account_number)
    if recipient_resp.get("status") != "success":
        return {"status": "failed", "error": {"message": f"Could not register transfer recipient: {recipient_resp}"}}
    recipient_id = recipient_resp["data"]["id"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FLW_API_BASE}/transfers",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Trace-Id": str(uuid.uuid4()),
                "X-Idempotency-Key": reference,
            },
            json={
                "action": "instant",
                "type": "bank",
                "reference": reference,
                "narration": narration,
                "payment_instruction": {
                    "amount": {"value": amount_naira, "applies_to": "destination_currency"},
                    "source_currency": "NGN",
                    "destination_currency": "NGN",
                    "recipient_id": recipient_id,
                },
            },
            timeout=20,
        )
        return resp.json()

