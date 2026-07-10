"""
Affiliate payout batching + execution.

Two-stage design, deliberately not fully automatic:
  1. generate_weekly_payout_batch() — runs on schedule, no human needed.
     Groups unpaid referrals by affiliate, computes commission, stages
     a payout_batches doc, and immediately flips every included referral
     to payout_status "batched" so it can never be claimed by a second
     batch generated before this one is confirmed (double-payout guard).
  2. confirm_payout_batch() — the ONE human checkpoint. Only this
     function ever calls the real Transfers API. One admin click processes
     every line item in a batch; a failure on one line item is recorded
     and the rest of the batch still proceeds.
"""
import uuid
from datetime import datetime, timezone

from bson import ObjectId

from ..config import get_settings
from .flutterwave import get_flw_token, create_transfer_recipient, create_transfer

settings = get_settings()

# Statuses the synchronous /transfers response can return that mean
# "Flutterwave accepted this, not yet a terminal failure" — a real
# production build would confirm via callback_url; for now this is the
# best signal available from the synchronous response alone.
NON_FAILURE_TRANSFER_STATUSES = {"SUCCESSFUL", "NEW", "PENDING", "INITIATED"}


async def generate_weekly_payout_batch(db) -> dict:
    """
    Returns the created batch dict, or None if there was nothing unpaid
    to batch (per the "don't create empty batches" rule).
    """
    unpaid = await db.referrals.find({"payout_status": "unpaid"}).to_list(None)
    if not unpaid:
        return None

    by_code = {}
    for r in unpaid:
        by_code.setdefault(r["affiliate_code"], []).append(r)

    now = datetime.now(timezone.utc)
    line_items = []
    total_amount = 0.0

    for code, refs in by_code.items():
        affiliate = await db.affiliates.find_one({"code": code})
        if not affiliate:
            # Orphaned referral (affiliate record deleted) — shouldn't
            # happen since affiliates are only ever deactivated, never
            # deleted, but skip defensively rather than crash the batch.
            continue

        amount_owed = round(
            sum(r["amount"] for r in refs) * (settings.AFFILIATE_COMMISSION_PERCENT / 100), 2
        )
        line_items.append({
            "affiliate_id": str(affiliate["_id"]),
            "affiliate_code": code,
            "affiliate_name": affiliate["name"],
            "affiliate_email": affiliate["email"],
            "bank_name": affiliate.get("bank_name"),
            "bank_account_number": affiliate.get("bank_account_number"),
            "bank_code": affiliate.get("bank_code"),
            "amount": amount_owed,
            "referral_ids": [str(r["_id"]) for r in refs],
            "transfer_status": "pending",
            "transfer_id": None,
            "transfer_error": None,
        })
        total_amount += amount_owed

    if not line_items:
        return None

    batch_doc = {
        "batch_id": f"PB-{uuid.uuid4().hex[:10].upper()}",
        "created_at": now,
        "status": "pending_confirmation",
        "line_items": line_items,
        "total_amount": round(total_amount, 2),
        "confirmed_at": None,
        "confirmed_by": None,
    }
    result = await db.payout_batches.insert_one(batch_doc)
    batch_doc["_id"] = result.inserted_id

    all_referral_ids = [ObjectId(rid) for item in line_items for rid in item["referral_ids"]]
    await db.referrals.update_many(
        {"_id": {"$in": all_referral_ids}},
        {"$set": {"payout_status": "batched", "batch_id": batch_doc["batch_id"]}},
    )

    return batch_doc


async def confirm_payout_batch(db, batch_id: str, confirmed_by: str) -> dict:
    """
    The one human-triggered action that moves real money. Processes every
    line item; one failure never blocks the rest of the batch.
    """
    batch = await db.payout_batches.find_one({"batch_id": batch_id})
    if not batch:
        raise ValueError("batch_not_found")
    if batch["status"] != "pending_confirmation":
        raise ValueError(f"batch_already_{batch['status']}")

    token = await get_flw_token()
    succeeded = 0
    failed = 0
    updated_line_items = []
    now = datetime.now(timezone.utc)

    for item in batch["line_items"]:
        referral_ids = [ObjectId(rid) for rid in item["referral_ids"]]

        # Re-check at execution time, not just at batch-generation time —
        # an affiliate can be deactivated in the gap between a batch being
        # staged and an admin confirming it, days later.
        still_batched = await db.referrals.count_documents({
            "_id": {"$in": referral_ids}, "payout_status": "batched"
        })
        if still_batched != len(referral_ids):
            item["transfer_status"] = "skipped"
            item["transfer_error"] = "One or more referrals no longer eligible (affiliate deactivated or already processed since this batch was generated)"
            updated_line_items.append(item)
            failed += 1
            continue

        try:
            affiliate = await db.affiliates.find_one({"_id": ObjectId(item["affiliate_id"])})
            if not affiliate:
                raise Exception("Affiliate record no longer exists")

            recipient_id = affiliate.get("flw_recipient_id")
            if not recipient_id:
                name_parts = affiliate["name"].strip().split(" ", 1)
                recipient_id = await create_transfer_recipient(
                    token,
                    account_number=affiliate["bank_account_number"],
                    bank_code=affiliate["bank_code"],
                    first_name=name_parts[0],
                    last_name=name_parts[1] if len(name_parts) > 1 else name_parts[0],
                )
                await db.affiliates.update_one(
                    {"_id": affiliate["_id"]}, {"$set": {"flw_recipient_id": recipient_id}}
                )

            transfer_reference = f"PAYOUT{uuid.uuid4().hex[:20].upper()}"
            result = await create_transfer(
                token, recipient_id, item["amount"], transfer_reference,
                narration=f"Affiliate payout - {batch_id}"[:180],
            )
            transfer_data = result.get("data", {})
            flw_status = transfer_data.get("status")
            is_ok = result.get("status") == "success" and flw_status in NON_FAILURE_TRANSFER_STATUSES

            await db.transfer_logs.insert_one({
                "affiliate_code": item["affiliate_code"],
                "batch_id": batch_id,
                "amount": item["amount"],
                "recipient_id": recipient_id,
                "transfer_reference": transfer_reference,
                "transfer_id": transfer_data.get("id"),
                "flw_status": flw_status,
                "raw_response": result,
                "error": None if is_ok else result.get("message"),
                "created_at": now,
            })

            if is_ok:
                item["transfer_status"] = "success"
                item["transfer_id"] = transfer_data.get("id")
                await db.referrals.update_many(
                    {"_id": {"$in": referral_ids}},
                    {"$set": {"payout_status": "paid", "paid_at": now}},
                )
                succeeded += 1
            else:
                item["transfer_status"] = "failed"
                item["transfer_error"] = result.get("message", "Unknown error")
                await db.referrals.update_many(
                    {"_id": {"$in": referral_ids}},
                    {"$set": {"payout_status": "failed", "payout_error": result.get("message")}},
                )
                failed += 1
        except Exception as e:
            item["transfer_status"] = "failed"
            item["transfer_error"] = str(e)
            await db.transfer_logs.insert_one({
                "affiliate_code": item["affiliate_code"],
                "batch_id": batch_id,
                "amount": item["amount"],
                "error": str(e),
                "created_at": now,
            })
            await db.referrals.update_many(
                {"_id": {"$in": referral_ids}},
                {"$set": {"payout_status": "failed", "payout_error": str(e)}},
            )
            failed += 1

        updated_line_items.append(item)

    final_status = "completed" if failed == 0 else "completed_with_errors"
    await db.payout_batches.update_one(
        {"_id": batch["_id"]},
        {"$set": {
            "status": final_status,
            "line_items": updated_line_items,
            "confirmed_at": now,
            "confirmed_by": confirmed_by,
        }},
    )

    return {
        "batch_id": batch_id,
        "status": final_status,
        "succeeded": succeeded,
        "failed": failed,
        "total_line_items": len(batch["line_items"]),
    }
