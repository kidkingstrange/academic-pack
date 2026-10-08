"""
Shared affiliate-creation path for both entry points — the admin-created
flow (routes/affiliates.py) and the public self-registration flow
(routes/affiliate_public.py) — so code generation, uniqueness handling,
and the record shape can never silently diverge between the two.
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
    bank_name: str = None,
    bank_code: str = None,
    account_number: str = None,
    account_name: str = None,
    invited_by: str = None,
    password_hash: str = None,
    account_activated: bool = False,
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

    parent_code = None
    if invited_by:
        clean_invite = invited_by.strip().upper()
        parent = await db.affiliates.find_one({"code": clean_invite, "active": {"$ne": False}})
        if parent:
            parent_code = clean_invite

    doc = {
        "code": resolved_code,
        "name": name,
        "email": email,
        "bank_name": (bank_name or "").strip(),
        "bank_code": (bank_code or "").strip(),
        "account_number": (account_number or "").strip(),
        "account_name": (account_name or "").strip(),
        "active": True,
        "source": source,
        "commission_percent": resolved_commission,
        "dashboard_token": secrets.token_urlsafe(24),
        "invited_by": parent_code,
        "account_activated": bool(account_activated or password_hash),
        "password_hash": password_hash,
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


import re
from typing import Optional

POPULAR_NIGERIAN_BANK_CODES = {
    "access": "044",
    "accessbank": "044",
    "accessdiamond": "063",
    "diamond": "063",
    "alat": "035",
    "alatbywema": "035",
    "carbon": "100026",
    "citibank": "023",
    "ecobank": "050",
    "fairmoney": "51318",
    "fidelity": "070",
    "fidelitybank": "070",
    "firstbank": "011",
    "firstbankofnigeria": "011",
    "fcmb": "214",
    "firstcitymonument": "214",
    "firstcitymonumentbank": "214",
    "globus": "00103",
    "globusbank": "00103",
    "gtb": "058",
    "gtbank": "058",
    "guarantytrust": "058",
    "guarantytrustbank": "058",
    "heritage": "030",
    "heritagebank": "030",
    "jaiz": "301",
    "jaizbank": "301",
    "keystone": "082",
    "keystonebank": "082",
    "kuda": "50211",
    "kudabank": "50211",
    "lotus": "303",
    "lotusbank": "303",
    "moniepoint": "50515",
    "moniepointmfb": "50515",
    "opay": "999992",
    "paycom": "999992",
    "palmpay": "999991",
    "polaris": "076",
    "polarisbank": "076",
    "providus": "101",
    "providusbank": "101",
    "rubies": "125",
    "sparkle": "51310",
    "stanbic": "039",
    "stanbicibtc": "039",
    "standardchartered": "068",
    "sterling": "232",
    "sterlingbank": "232",
    "taj": "302",
    "tajbank": "302",
    "titan": "102",
    "titantrust": "102",
    "union": "032",
    "unionbank": "032",
    "uba": "033",
    "unitedbankforafrica": "033",
    "unity": "215",
    "unitybank": "215",
    "vfd": "566",
    "vbank": "566",
    "wema": "035",
    "wemabank": "035",
    "zenith": "057",
    "zenithbank": "057",
}


async def resolve_bank_code_by_name(bank_name: str) -> Optional[str]:
    """
    Attempt to map a Nigerian bank name or colloquial alias to its Paystack NUBAN bank code.
    Checks static canonical dictionary first, then falls back to Paystack's live bank API.
    """
    if not bank_name:
        return None
    raw = bank_name.strip().lower()
    norm = re.sub(r"[^a-z0-9]", "", raw)
    if norm in POPULAR_NIGERIAN_BANK_CODES:
        return POPULAR_NIGERIAN_BANK_CODES[norm]
    for key, code in POPULAR_NIGERIAN_BANK_CODES.items():
        if key in norm:
            return code
    try:
        from ..services.paystack import list_banks
        banks = await list_banks()
        for b in banks:
            b_norm = re.sub(r"[^a-z0-9]", "", (b.get("name") or "").lower())
            if norm == b_norm or norm in b_norm or b_norm in norm:
                return str(b.get("code") or "")
    except Exception:
        pass
    return None


async def ensure_affiliate_subaccount(db, affiliate: dict) -> dict:
    """
    Create or update this affiliate's Paystack subaccount so future
    referred sales can split to their bank account instantly at the
    point of payment, bypassing the manual commission/payout-batch
    pipeline entirely for them going forward.

    No-ops and returns the affiliate unchanged if bank details are
    incomplete (most commonly a missing bank_code) — such an affiliate
    simply stays on the existing manual payout system rather than
    blocking whatever caller triggered this (affiliate creation, a bank
    details update, or a commission-rate change).
    """
    from ..services.paystack import create_subaccount, update_subaccount

    bank_code = (affiliate.get("bank_code") or "").strip()
    account_number = (affiliate.get("account_number") or "").strip()
    bank_name = (affiliate.get("bank_name") or "").strip()

    if not bank_code and bank_name:
        resolved = await resolve_bank_code_by_name(bank_name)
        if resolved:
            bank_code = resolved
            affiliate["bank_code"] = bank_code
            if db is not None and "_id" in affiliate:
                try:
                    await db.affiliates.update_one(
                        {"_id": affiliate["_id"]},
                        {"$set": {"bank_code": bank_code}}
                    )
                except Exception:
                    pass

    if not bank_code or not account_number:
        return affiliate

    business_name = (affiliate.get("account_name") or affiliate.get("name") or affiliate.get("code")).strip()
    commission_percent = affiliate.get("commission_percent", 0) or 0
    # percentage_charge is Paystack's field for what the MAIN account
    # keeps — the affiliate's subaccount receives the rest, i.e. their
    # actual commission rate.
    percentage_charge = round(100 - commission_percent, 2)

    existing_code = affiliate.get("subaccount_code")
    try:
        if existing_code:
            resp = await update_subaccount(
                existing_code,
                business_name=business_name,
                bank_code=bank_code,
                account_number=account_number,
                percentage_charge=percentage_charge,
            )
            subaccount_code = existing_code
        else:
            resp = await create_subaccount(
                business_name=business_name,
                bank_code=bank_code,
                account_number=account_number,
                percentage_charge=percentage_charge,
                description=f"Affiliate {affiliate.get('code')}",
            )
            subaccount_code = (resp.get("data") or {}).get("subaccount_code")
    except Exception as e:
        print(f"⚠️ Paystack subaccount sync failed for affiliate {affiliate.get('code')}: {e}")
        return affiliate

    if not resp.get("status") or not subaccount_code:
        print(f"⚠️ Paystack subaccount sync rejected for affiliate {affiliate.get('code')}: {resp.get('message')}")
        return affiliate

    update_fields = {
        "subaccount_code": subaccount_code,
        "subaccount_percentage_charge": percentage_charge,
        "subaccount_synced_at": datetime.now(timezone.utc),
    }
    await db.affiliates.update_one({"_id": affiliate["_id"]}, {"$set": update_fields})
    affiliate.update(update_fields)
    return affiliate


async def get_or_create_customer_affiliate(
    db,
    *,
    name: str,
    email: str,
    invited_by: str = None,
) -> tuple[dict, bool]:
    """
    Finds an existing affiliate by email, or auto-provisions a new affiliate
    record for a paying customer with source='auto_customer_upgrade'.
    Returns (affiliate_doc, created_bool).
    """
    clean_email = (email or "").lower().strip()
    if not clean_email:
        return None, False

    existing = await db.affiliates.find_one({"email": clean_email})
    if existing:
        return existing, False

    clean_name = (name or "").strip() or "Valued Ambassador"
    doc = await create_affiliate_record(
        db,
        name=clean_name,
        email=clean_email,
        source="auto_customer_upgrade",
        invited_by=invited_by,
    )
    return doc, True

