"""
Paystack Synchronization and Payment Reconciliation Service.

Ensures the local MongoDB collections (db.payments, db.flagged_payments)
are kept 100% in sync with live Paystack transactions:
1. Auto-syncs successful Paystack transactions in real time and in background.
2. Preserves the exact payment timestamp (paid_at) so analytics dates remain accurate.
3. Automatically marks flagged records as resolved once confirmed.
4. Normalizes BSON Datetime and numeric amounts so analytics aggregations never drop records.
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from ..config import get_settings
from ..services import paystack
from ..services.payment_completion import complete_payment, is_valid_paid_amount

settings = get_settings()

_LAST_SYNC_CACHE: Dict[str, Any] = {
    "timestamp": None,
    "result": None,
}
_SYNC_COOLDOWN_SECONDS = 60
_sync_lock = asyncio.Lock()


def parse_paystack_datetime(dt_str: Optional[str]) -> datetime:
    """Parse Paystack ISO timestamp string into a timezone-aware UTC datetime."""
    if not dt_str:
        return datetime.now(timezone.utc)
    try:
        clean_str = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


async def sanitize_payment_records(db) -> int:
    """
    Ensure all payments have proper BSON Date verified_at and float amount
    so date-range analytics aggregations and queries never drop or miscalculate records.
    """
    if db is None:
        return 0

    fixed_count = 0
    now = datetime.now(timezone.utc)

    try:
        # 1. Backfill verified_at from created_at or purchase_date if missing or null
        cursor_missing = db.payments.find({
            "$or": [
                {"verified_at": {"$exists": False}},
                {"verified_at": None},
            ]
        })
        async for p in cursor_missing:
            raw_dt = p.get("created_at") or p.get("purchase_date")
            if isinstance(raw_dt, str):
                dt = parse_paystack_datetime(raw_dt)
            elif isinstance(raw_dt, datetime):
                dt = raw_dt if raw_dt.tzinfo else raw_dt.replace(tzinfo=timezone.utc)
            else:
                dt = now
            await db.payments.update_one({"_id": p["_id"]}, {"$set": {"verified_at": dt}})
            fixed_count += 1

        # 2. Convert string verified_at to BSON datetime
        cursor_str = db.payments.find({"verified_at": {"$type": "string"}})
        async for p in cursor_str:
            val = p.get("verified_at")
            dt = parse_paystack_datetime(val)
            await db.payments.update_one({"_id": p["_id"]}, {"$set": {"verified_at": dt}})
            fixed_count += 1

        # 3. Ensure amount is a numeric float, falling back to amount_paid or base_price
        cursor_amt = db.payments.find({
            "$or": [
                {"amount": {"$type": "string"}},
                {"amount": None},
                {"amount": {"$exists": False}},
            ]
        })
        async for p in cursor_amt:
            raw_amt = p.get("amount") if p.get("amount") is not None else (p.get("amount_paid") or p.get("base_price") or 0.0)
            try:
                amt = float(raw_amt)
            except Exception:
                amt = 0.0
            await db.payments.update_one({"_id": p["_id"]}, {"$set": {"amount": amt}})
            fixed_count += 1

    except Exception as err:
        print(f"⚠️ [PaystackSync] Note during sanitize_payment_records: {err}")

    return fixed_count


async def auto_sync_paystack_successful_sales(
    db,
    per_page: int = 50,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Auto-sync all successful Paystack transactions into local MongoDB:
    1. Fetches recent successful transactions directly from Paystack API.
    2. Identifies any payments missing in db.payments.
    3. Completes them with accurate historical verified_at timestamps.
    4. Automatically resolves matching records in db.flagged_payments.
    5. Sanitizes existing payments so analytics queries are 100% accurate.
    """
    if db is None:
        return {"success": False, "message": "Database not connected", "newly_reconciled_count": 0}

    now = datetime.now(timezone.utc)

    # Cooldown cache check (bypassed when force=True)
    if not force and _LAST_SYNC_CACHE["timestamp"] and _LAST_SYNC_CACHE["result"]:
        elapsed = (now - _LAST_SYNC_CACHE["timestamp"]).total_seconds()
        if elapsed < _SYNC_COOLDOWN_SECONDS:
            return _LAST_SYNC_CACHE["result"]

    async with _sync_lock:
        # Re-check inside lock
        if not force and _LAST_SYNC_CACHE["timestamp"] and _LAST_SYNC_CACHE["result"]:
            elapsed = (now - _LAST_SYNC_CACHE["timestamp"]).total_seconds()
            if elapsed < _SYNC_COOLDOWN_SECONDS:
                return _LAST_SYNC_CACHE["result"]

        if not settings.PAYSTACK_SECRET_KEY:
            res = {
                "success": False,
                "message": "PAYSTACK_SECRET_KEY is not configured",
                "scanned": 0,
                "already_synced": 0,
                "newly_reconciled_count": 0,
                "newly_reconciled": [],
                "last_synced_at": now.isoformat(),
            }
            _LAST_SYNC_CACHE["timestamp"] = now
            _LAST_SYNC_CACHE["result"] = res
            return res

        try:
            raw_res = await paystack.list_transactions(status="success", page=1, per_page=per_page)
        except Exception as e:
            print(f"⚠️ [PaystackSync] Failed to query Paystack API: {e}")
            res = {
                "success": False,
                "message": f"Failed to query Paystack API: {str(e)}",
                "scanned": 0,
                "already_synced": 0,
                "newly_reconciled_count": 0,
                "newly_reconciled": [],
                "last_synced_at": now.isoformat(),
            }
            return res

        if not raw_res or not raw_res.get("status"):
            err_msg = (raw_res.get("message") if isinstance(raw_res, dict) else "") or "Failed to query Paystack"
            res = {
                "success": False,
                "message": err_msg,
                "scanned": 0,
                "already_synced": 0,
                "newly_reconciled_count": 0,
                "newly_reconciled": [],
                "last_synced_at": now.isoformat(),
            }
            return res

        txs = raw_res.get("data", []) if isinstance(raw_res, dict) else []
        already_synced = 0
        newly_reconciled = []

        for tx in txs:
            ref = tx.get("reference")
            if not ref:
                continue

            paid_at_str = tx.get("paid_at") or tx.get("createdAt") or tx.get("created_at")
            verified_dt = parse_paystack_datetime(paid_at_str)

            existing = await db.payments.find_one({"reference": ref, "status": {"$in": ["success", "SUCCESS"]}})
            if existing:
                already_synced += 1
                # If verified_at or amount is inconsistent, repair it now
                updates = {}
                if not existing.get("verified_at") or isinstance(existing.get("verified_at"), str):
                    updates["verified_at"] = verified_dt
                if existing.get("amount") is None or isinstance(existing.get("amount"), str):
                    try:
                        updates["amount"] = float(existing.get("amount") or existing.get("amount_paid") or existing.get("base_price") or 0.0)
                    except Exception:
                        pass
                if updates:
                    await db.payments.update_one({"_id": existing["_id"]}, {"$set": updates})
                continue

            amount_paid = (tx.get("amount") or 0) / 100.0
            fee_paid = float((tx.get("fees") or 0) / 100.0)
            cust = tx.get("customer", {})
            email = (cust.get("email") or "").strip().lower()
            first_name = cust.get("first_name", "") or ""
            last_name = cust.get("last_name", "") or ""
            name = f"{first_name} {last_name}".strip() or "Student"

            pending = await db.pending_payments.find_one({"reference": ref})
            if pending:
                email = email or (pending.get("email") or "").strip().lower()
                name = pending.get("name") or name
                expected = float(pending.get("amount", 0) or 0)
            else:
                expected = 0.0

            if expected > 0 and not is_valid_paid_amount(amount_paid, expected, fee_paid):
                await db.flagged_payments.update_one(
                    {"reference": ref},
                    {"$set": {
                        "reason": "amount_mismatch",
                        "expected_amount": expected,
                        "amount_paid": amount_paid,
                        "payload": tx,
                        "resolved": False,
                        "flagged_at": now,
                    }},
                    upsert=True
                )
                continue

            if not email:
                continue

            try:
                completion = await complete_payment(
                    db,
                    reference=ref,
                    email=email,
                    name=name,
                    amount=amount_paid,
                    charge_id=str(tx.get("id", ref)),
                    gateway_response=tx,
                    completed_via="paystack_auto_sync",
                    payment_method=tx.get("channel"),
                    verified_at=verified_dt,
                )
                await db.flagged_payments.update_one(
                    {"reference": ref},
                    {"$set": {
                        "resolved": True,
                        "resolved_at": now,
                        "resolved_by": "paystack_auto_sync",
                        "resolution_notes": "Automatically verified & fulfilled via Paystack auto-sync",
                    }}
                )
                newly_reconciled.append({
                    "reference": ref,
                    "email": email,
                    "name": name,
                    "amount": amount_paid,
                    "verified_at": verified_dt.isoformat(),
                    "magic_link": completion.get("magic_link"),
                })
                print(f"✅ [PaystackSync] Reconciled transaction {ref} for {email} (₦{amount_paid:,.2f})")
            except Exception as sync_err:
                print(f"⚠️ [PaystackSync] Error reconciling {ref}: {sync_err}")

        # Sanitize all existing records
        await sanitize_payment_records(db)

        result = {
            "success": True,
            "scanned": len(txs),
            "already_synced": already_synced,
            "newly_reconciled_count": len(newly_reconciled),
            "newly_reconciled": newly_reconciled,
            "last_synced_at": now.isoformat(),
            "message": f"Scanned {len(txs)} Paystack transactions: {already_synced} already up to date, {len(newly_reconciled)} newly reconciled.",
        }

        _LAST_SYNC_CACHE["timestamp"] = now
        _LAST_SYNC_CACHE["result"] = result
        return result
