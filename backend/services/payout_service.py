"""
Biweekly affiliate commission payouts.

Two separate money flows live here, kept deliberately independent:
  1. Affiliate payout batches — what's owed to affiliates, paid out of
     the Flutterwave NGN payout balance in a reviewable, admin-approved
     batch (build_pending_batch never moves money; only send_batch does,
     and only after an admin explicitly approves).
  2. Your own settlement withdrawal — pulling your share (balance minus
     everything still owed to affiliates) out to your personal bank,
     since disabling Flutterwave's auto-settlement means nothing leaves
     the payout balance automatically anymore, including your own cut.

A referral only flips to commission_status="paid" when its specific
transfer item actually succeeds. Anything that fails (bad account,
insufficient balance, missing bank_code) stays "unpaid" and is picked up
again automatically by the next batch — no separate retry queue needed.
"""
import re
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ReturnDocument

from ..config import get_settings
from .flutterwave import create_transfer, get_ngn_balance

settings = get_settings()


def _clean_reference(raw: str) -> str:
    """Flutterwave transfer references must be alphanumeric, 6-42 chars."""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw)
    return cleaned[:42]


async def build_pending_batch(db, period_start: datetime, period_end: datetime) -> dict:
    """
    Group all currently-unpaid commissions by affiliate into a new
    payout_batches document (status "pending_approval"). Read-only
    against Flutterwave — only touches MongoDB. Returns None if there's
    nothing owed right now.
    """
    referrals = await db.referrals.find({"commission_status": "unpaid"}).to_list(10000)
    if not referrals:
        return None

    by_affiliate = {}
    for r in referrals:
        by_affiliate.setdefault(r["affiliate_code"], []).append(r)

    items = []
    total_amount = 0.0
    for code, refs in by_affiliate.items():
        affiliate = await db.affiliates.find_one({"code": code})
        if not affiliate:
            # Orphaned referral (affiliate record deleted after the sale)
            # — don't let it block the rest of the batch.
            continue

        amount = round(sum(r.get("commission_amount", 0) or 0 for r in refs), 2)
        bank_code = (affiliate.get("bank_code") or "").strip()
        items.append({
            "affiliate_code": code,
            "affiliate_name": affiliate.get("name", ""),
            "bank_name": affiliate.get("bank_name", ""),
            "bank_code": bank_code,
            "account_number": affiliate.get("account_number", ""),
            "account_name": affiliate.get("account_name", ""),
            "amount": amount,
            "referral_ids": [r["_id"] for r in refs],
            "transfer_status": "pending" if bank_code else "blocked_missing_bank_code",
            "flw_transfer_id": None,
            "error": None,
        })
        total_amount += amount

    batch = {
        "period_start": period_start,
        "period_end": period_end,
        "created_at": datetime.now(timezone.utc),
        "status": "pending_approval",
        "items": items,
        "total_amount": round(total_amount, 2),
        "approved_at": None,
    }
    result = await db.payout_batches.insert_one(batch)
    batch["_id"] = result.inserted_id
    return batch


async def send_batch(db, batch_id: str) -> dict:
    """
    Execute every sendable item in a batch. Each affiliate transfer is
    independent — one failure never blocks the others. Checks the live
    Flutterwave balance before sending anything, so a batch that exceeds
    what's actually available is rejected up front rather than partially
    draining the balance.
    """
    try:
        oid = ObjectId(batch_id)
    except Exception:
        raise ValueError("Invalid batch ID format")

    # Atomic CAS claim: transition status from pending_approval/failed_partial to sending
    batch = await db.payout_batches.find_one_and_update(
        {
            "_id": oid,
            "status": {"$in": ["pending_approval", "failed_partial"]}
        },
        {"$set": {"status": "sending"}},
        return_document=ReturnDocument.AFTER
    )
    if not batch:
        existing = await db.payout_batches.find_one({"_id": oid})
        if not existing:
            raise ValueError("Batch not found")
        raise ValueError(f"Batch already {existing['status']}")

    items = batch["items"]
    sendable = [i for i in items if i["transfer_status"] in ("pending", "failed")]
    sendable_total = round(sum(i["amount"] for i in sendable), 2)

    balance_resp = await get_ngn_balance()
    if balance_resp.get("status") != "success":
        # Revert status on balance check failure
        await db.payout_batches.update_one({"_id": oid}, {"$set": {"status": "failed_partial"}})
        raise ValueError(f"Could not read Flutterwave balance: {balance_resp.get('message') or balance_resp}")
    available = (balance_resp.get("data") or {}).get("available_balance", 0)
    if available < sendable_total:
        # Revert status on insufficient balance
        await db.payout_batches.update_one({"_id": oid}, {"$set": {"status": "failed_partial"}})
        raise ValueError(
            f"Insufficient balance: available ₦{available:,.2f}, batch needs ₦{sendable_total:,.2f}"
        )

    any_failed = False
    for idx, item in enumerate(items):
        if item["transfer_status"] not in ("pending", "failed"):
            continue
        if not item.get("bank_code"):
            item["transfer_status"] = "blocked_missing_bank_code"
            any_failed = True
            await db.payout_batches.update_one({"_id": batch["_id"]}, {"$set": {f"items.{idx}": item}})
            continue

        # Deterministic transfer reference derived from batch ID + affiliate code
        # (omitting random UUID so retries reuse Flutterwave's idempotency key)
        reference = _clean_reference(f"PAYOUT{batch['_id']}{item['affiliate_code']}")
        try:
            resp = await create_transfer(
                bank_code=item["bank_code"],
                account_number=item["account_number"],
                amount_naira=item["amount"],
                reference=reference,
                narration=f"Affiliate commission - {item['affiliate_code']}",
            )
            if resp.get("status") == "success":
                item["transfer_status"] = "success"
                item["flw_transfer_id"] = (resp.get("data") or {}).get("id")
                item["error"] = None
                now = datetime.now(timezone.utc)
                await db.referrals.update_many(
                    {
                        "_id": {"$in": item["referral_ids"]},
                        "commission_status": "unpaid"
                    },
                    {"$set": {"commission_status": "paid", "paid_at": now, "payout_reference": reference}},
                )
            else:
                item["transfer_status"] = "failed"
                item["error"] = resp.get("message") or str(resp)
                any_failed = True
        except Exception as e:
            item["transfer_status"] = "failed"
            item["error"] = str(e)
            any_failed = True

        await db.payout_batches.update_one({"_id": batch["_id"]}, {"$set": {f"items.{idx}": item}})

    final_status = "failed_partial" if any_failed else "completed"
    await db.payout_batches.update_one(
        {"_id": batch["_id"]},
        {"$set": {"status": final_status, "approved_at": datetime.now(timezone.utc)}},
    )
    return await db.payout_batches.find_one({"_id": batch["_id"]})


async def get_settlement_summary(db) -> dict:
    """
    What's actually yours to withdraw: the Flutterwave payout balance
    minus everything still owed to affiliates across ALL batches (not
    just the latest one — includes anything rolled over from a failed
    item). Read-only.
    """
    balance_resp = await get_ngn_balance()
    if balance_resp.get("status") != "success":
        raise ValueError(f"Could not read Flutterwave balance: {balance_resp.get('message') or balance_resp}")
    flw_balance = (balance_resp.get("data") or {}).get("available_balance", 0)

    pipeline = [
        {"$match": {"commission_status": "unpaid"}},
        {"$group": {"_id": None, "total": {"$sum": "$commission_amount"}}},
    ]
    result = await db.referrals.aggregate(pipeline).to_list(1)
    reserved = round(result[0]["total"], 2) if result else 0.0

    return {
        "flutterwave_balance": flw_balance,
        "reserved_for_affiliates": reserved,
        "available_to_withdraw": round(flw_balance - reserved, 2),
    }


async def withdraw_settlement_share(db, amount_naira: float) -> dict:
    """
    Transfer your own share out of the Flutterwave payout balance to the
    settlement bank account configured via SETTLEMENT_* env vars. Records
    an audit entry in settlement_withdrawals regardless of outcome.
    """
    if not settings.SETTLEMENT_BANK_CODE or not settings.SETTLEMENT_ACCOUNT_NUMBER:
        raise ValueError("SETTLEMENT_BANK_CODE / SETTLEMENT_ACCOUNT_NUMBER not configured")

    reference = _clean_reference(f"SETTLE{uuid.uuid4().hex}")
    now = datetime.now(timezone.utc)
    record = {
        "amount": amount_naira,
        "bank_code": settings.SETTLEMENT_BANK_CODE,
        "account_number": settings.SETTLEMENT_ACCOUNT_NUMBER,
        "reference": reference,
        "created_at": now,
        "status": "pending",
        "flw_transfer_id": None,
        "error": None,
    }
    result = await db.settlement_withdrawals.insert_one(record)

    try:
        resp = await create_transfer(
            bank_code=settings.SETTLEMENT_BANK_CODE,
            account_number=settings.SETTLEMENT_ACCOUNT_NUMBER,
            amount_naira=amount_naira,
            reference=reference,
            narration="Owner settlement withdrawal",
        )
        if resp.get("status") == "success":
            update = {"status": "success", "flw_transfer_id": (resp.get("data") or {}).get("id")}
        else:
            update = {"status": "failed", "error": resp.get("message") or str(resp)}
    except Exception as e:
        update = {"status": "failed", "error": str(e)}

    await db.settlement_withdrawals.update_one({"_id": result.inserted_id}, {"$set": update})
    record.update(update)
    record["_id"] = result.inserted_id
    return record
