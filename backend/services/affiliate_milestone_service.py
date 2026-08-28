"""
Affiliate Milestone & Recruiter Referral Bonus Engine.

Rules:
1. Direct Milestone: When an affiliate reaches 10 sales, they unlock a ₦10,000 cash bonus.
2. Recruiter Bonus: When an invited affiliate reaches 10 sales, the parent affiliate
   who invited them unlocks a ₦5,000 referral bonus.
3. Fully idempotent: Guarded by database unique index and existence checks.
"""
import re
import secrets
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from ..config import get_settings
from .paystack import create_transfer, get_paystack_balance
from .email_service import send_email

settings = get_settings()

DIRECT_10_SALES_BONUS = 10000.0
PARENT_RECRUITER_BONUS = 5000.0
MILESTONE_SALES_TARGET = 10


def _clean_transfer_reference(raw: str) -> str:
    """Paystack transfer references must be alphanumeric, 6-50 chars."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", raw)
    return cleaned[:50]


async def disburse_single_milestone(db, milestone_id) -> dict:
    """
    Attempt instant automated transfer of a single milestone bonus.
    Atomic CAS transitions status 'unlocked' -> 'processing' -> 'paid' (or 'unlocked' on failure).
    """
    if db is None or not milestone_id:
        return {"success": False, "reason": "invalid_parameters"}

    try:
        oid = ObjectId(milestone_id) if not isinstance(milestone_id, ObjectId) else milestone_id
    except Exception:
        return {"success": False, "reason": "invalid_id"}

    # 1. Atomic claim
    milestone = await db.affiliate_milestones.find_one_and_update(
        {"_id": oid, "status": "unlocked"},
        {"$set": {"status": "processing", "processing_started_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if not milestone:
        return {"success": False, "reason": "already_processing_or_paid"}

    affiliate_code = milestone.get("affiliate_code")
    affiliate = await db.affiliates.find_one({"code": affiliate_code})
    if not affiliate:
        await db.affiliate_milestones.update_one(
            {"_id": oid},
            {"$set": {"status": "unlocked", "last_error": "affiliate_not_found"}}
        )
        return {"success": False, "reason": "affiliate_not_found"}

    bank_code = (affiliate.get("bank_code") or "").strip()
    account_number = (affiliate.get("account_number") or "").strip()
    account_name = (affiliate.get("account_name") or affiliate.get("name", "Affiliate")).strip()

    if not bank_code or not account_number:
        # Revert to unlocked — will be picked up when affiliate updates bank details
        await db.affiliate_milestones.update_one(
            {"_id": oid},
            {"$set": {"status": "unlocked", "last_error": "missing_bank_details"}}
        )
        return {"success": False, "reason": "missing_bank_details"}

    amount = float(milestone.get("amount", 0))
    if amount <= 0:
        await db.affiliate_milestones.update_one(
            {"_id": oid},
            {"$set": {"status": "unlocked", "last_error": "invalid_amount"}}
        )
        return {"success": False, "reason": "invalid_amount"}

    # 2. Check Paystack Balance
    try:
        balance_resp = await get_paystack_balance()
        if balance_resp.get("status") == "success":
            avail = (balance_resp.get("data") or {}).get("available_balance", 0)
            if avail < amount:
                print(f"⚠️ Paystack balance low (₦{avail:,.2f} < ₦{amount:,.2f}) for milestone {oid}")
                await db.affiliate_milestones.update_one(
                    {"_id": oid},
                    {"$set": {"status": "unlocked", "last_error": f"insufficient_balance (avail: ₦{avail:,.2f})"}}
                )
                return {"success": False, "reason": "insufficient_balance"}
    except Exception as e:
        print(f"⚠️ Warning checking balance: {e}")

    # 3. Create Transfer Reference
    short_id = str(oid)[-8:]
    rand_suffix = secrets.token_hex(3).upper()
    ref = _clean_transfer_reference(f"MS_{short_id}_{rand_suffix}")
    narration = f"Academic Pack Milestone ({milestone.get('type')})"[:100]

    try:
        transfer_resp = await create_transfer(
            bank_code=bank_code,
            account_number=account_number,
            amount_naira=amount,
            reference=ref,
            narration=narration,
            recipient_name=account_name,
        )

        if transfer_resp.get("status") == "success":
            transfer_data = transfer_resp.get("data", {})
            now = datetime.now(timezone.utc)
            await db.affiliate_milestones.update_one(
                {"_id": oid},
                {
                    "$set": {
                        "status": "paid",
                        "paid_at": now,
                        "transfer_reference": ref,
                        "transfer_code": transfer_data.get("transfer_code"),
                        "paystack_transfer_id": transfer_data.get("id"),
                        "bank_name": affiliate.get("bank_name"),
                        "account_number": account_number,
                        "account_name": account_name,
                        "last_error": None,
                    }
                }
            )
            print(f"💸 Milestone Bonus (₦{amount:,.2f}) paid to {affiliate_code} ({account_name} - {account_number}) | Ref: {ref}")

            # Notify Admin
            admin_email = settings.ADMIN_EMAIL
            if admin_email:
                admin_html = f"""
                <h3>💸 Automated Milestone Bonus Transferred</h3>
                <p><strong>Affiliate:</strong> {affiliate.get('name')} ({affiliate_code})</p>
                <p><strong>Type:</strong> {milestone.get('description')}</p>
                <p><strong>Amount:</strong> ₦{amount:,.2f}</p>
                <p><strong>Bank:</strong> {affiliate.get('bank_name')} ({account_number} - {account_name})</p>
                <p><strong>Transfer Reference:</strong> {ref}</p>
                """
                await send_email(admin_email, f"Automated Milestone Payout: ₦{amount:,.2f} to {affiliate.get('name')}", admin_html)

            return {
                "success": True,
                "amount": amount,
                "transfer_reference": ref,
                "bank_name": affiliate.get("bank_name"),
                "account_number": account_number,
                "recipient": f"{account_name} ({account_number})",
            }
        else:
            err = transfer_resp.get("error") or transfer_resp.get("message") or "Transfer initiation failed"
            print(f"❌ Paystack transfer failed for milestone {oid}: {err}")
            await db.affiliate_milestones.update_one(
                {"_id": oid},
                {
                    "$set": {
                        "status": "unlocked",
                        "last_error": str(err),
                        "failed_at": datetime.now(timezone.utc),
                    }
                }
            )
            return {"success": False, "reason": str(err)}

    except Exception as e:
        print(f"❌ Exception in milestone transfer {oid}: {e}")
        await db.affiliate_milestones.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": "unlocked",
                    "last_error": str(e),
                    "failed_at": datetime.now(timezone.utc),
                }
            }
        )
        return {"success": False, "reason": str(e)}


async def auto_disburse_pending_milestones_for_affiliate(db, affiliate_code: str) -> list:
    """
    Find all 'unlocked' milestones for an affiliate and trigger automated disbursement.
    """
    if not affiliate_code or db is None:
        return []

    unlocked_milestones = await db.affiliate_milestones.find({
        "affiliate_code": affiliate_code,
        "status": "unlocked",
    }).to_list(100)

    results = []
    for m in unlocked_milestones:
        res = await disburse_single_milestone(db, m["_id"])
        results.append({"milestone_id": str(m["_id"]), **res})
    return results


async def auto_disburse_all_pending_milestones(db) -> list:
    """
    Find all 'unlocked' milestones across all affiliates that have valid bank details,
    and trigger automated disbursement.
    """
    if db is None:
        return []

    unlocked_milestones = await db.affiliate_milestones.find({
        "status": "unlocked"
    }).to_list(500)

    results = []
    for m in unlocked_milestones:
        aff = await db.affiliates.find_one({"code": m.get("affiliate_code")})
        if aff and (aff.get("bank_code") or "").strip() and (aff.get("account_number") or "").strip():
            res = await disburse_single_milestone(db, m["_id"])
            results.append({"milestone_id": str(m["_id"]), **res})
    return results


async def check_and_trigger_milestones(db, affiliate_code: str) -> dict:
    """
    Check if an affiliate has reached the 10-sale milestone, and if so:
    1. Unlocks the ₦10,000 direct bonus for the affiliate and attempts instant Paystack transfer.
    2. Unlocks the ₦5,000 recruiter bonus for their parent affiliate (if any) and attempts instant transfer.
    3. Queues email notifications with transfer status.
    """
    if not affiliate_code or db is None:
        return {"direct_milestone_triggered": False, "parent_milestone_triggered": False}

    affiliate = await db.affiliates.find_one({"code": affiliate_code})
    if not affiliate:
        return {"direct_milestone_triggered": False, "parent_milestone_triggered": False}

    now = datetime.now(timezone.utc)
    sales_count = await db.referrals.count_documents({"affiliate_code": affiliate_code})
    
    direct_triggered = False
    parent_triggered = False

    if sales_count >= MILESTONE_SALES_TARGET:
        # ── 1. Direct Milestone for Selling Affiliate (₦10,000) ──────────────
        existing_direct = await db.affiliate_milestones.find_one({
            "affiliate_code": affiliate_code,
            "type": "direct_10_sales",
        })
        if not existing_direct:
            milestone_doc = {
                "affiliate_code": affiliate_code,
                "type": "direct_10_sales",
                "subaffiliate_code": None,
                "amount": DIRECT_10_SALES_BONUS,
                "status": "unlocked",
                "sales_count": sales_count,
                "description": f"10-Sale Milestone Bonus (₦{int(DIRECT_10_SALES_BONUS):,})",
                "created_at": now,
                "paid_at": None,
            }
            try:
                ins_res = await db.affiliate_milestones.insert_one(milestone_doc)
                direct_triggered = True
                print(f"🏆 Direct 10-Sale Milestone (₦10,000) unlocked for {affiliate_code} ({affiliate['name']})")

                # Attempt instant automated bank payout
                payout_res = await disburse_single_milestone(db, ins_res.inserted_id)
                is_transferred = payout_res.get("success", False)

                # Queue celebratory email
                dashboard_link = f"{settings.APP_URL}/affiliate/dashboard?token={affiliate.get('dashboard_token', '')}"
                await db.email_queue.insert_one({
                    "kind": "affiliate_direct_milestone",
                    "email": affiliate["email"],
                    "name": affiliate["name"],
                    "code": affiliate_code,
                    "bonus_amount": DIRECT_10_SALES_BONUS,
                    "sales_count": sales_count,
                    "dashboard_link": dashboard_link,
                    "is_transferred": is_transferred,
                    "transfer_reference": payout_res.get("transfer_reference", ""),
                    "bank_name": payout_res.get("bank_name", affiliate.get("bank_name", "")),
                    "account_number": payout_res.get("account_number", affiliate.get("account_number", "")),
                    "scheduled_at": now,
                    "status": "pending",
                    "retry_count": 0,
                    "sent_at": None,
                    "error": None,
                })
            except DuplicateKeyError:
                pass

        # ── 2. Recruiter Bonus for Parent Affiliate (₦5,000) ──────────────────
        parent_code = affiliate.get("invited_by")
        if parent_code:
            parent_affiliate = await db.affiliates.find_one({"code": parent_code, "active": True})
            if parent_affiliate:
                existing_parent_bonus = await db.affiliate_milestones.find_one({
                    "affiliate_code": parent_code,
                    "type": "referral_subaffiliate_10_sales",
                    "subaffiliate_code": affiliate_code,
                })
                if not existing_parent_bonus:
                    parent_doc = {
                        "affiliate_code": parent_code,
                        "type": "referral_subaffiliate_10_sales",
                        "subaffiliate_code": affiliate_code,
                        "subaffiliate_name": affiliate.get("name", "Your invited affiliate"),
                        "amount": PARENT_RECRUITER_BONUS,
                        "status": "unlocked",
                        "sales_count": sales_count,
                        "description": f"Recruiter Bonus (₦{int(PARENT_RECRUITER_BONUS):,}) — {affiliate.get('name')} reached 10 sales",
                        "created_at": now,
                        "paid_at": None,
                    }
                    try:
                        ins_parent_res = await db.affiliate_milestones.insert_one(parent_doc)
                        parent_triggered = True
                        print(f"🎉 Recruiter Bonus (₦5,000) unlocked for {parent_code} ({parent_affiliate['name']}) via {affiliate_code}")

                        # Attempt instant automated bank payout to parent
                        parent_payout_res = await disburse_single_milestone(db, ins_parent_res.inserted_id)
                        parent_is_transferred = parent_payout_res.get("success", False)

                        # Queue celebratory email to parent
                        parent_dashboard_link = f"{settings.APP_URL}/affiliate/dashboard?token={parent_affiliate.get('dashboard_token', '')}"
                        await db.email_queue.insert_one({
                            "kind": "affiliate_parent_referral_bonus",
                            "email": parent_affiliate["email"],
                            "name": parent_affiliate["name"],
                            "code": parent_code,
                            "subaffiliate_name": affiliate.get("name", "Your invited affiliate"),
                            "bonus_amount": PARENT_RECRUITER_BONUS,
                            "dashboard_link": parent_dashboard_link,
                            "is_transferred": parent_is_transferred,
                            "transfer_reference": parent_payout_res.get("transfer_reference", ""),
                            "bank_name": parent_payout_res.get("bank_name", parent_affiliate.get("bank_name", "")),
                            "account_number": parent_payout_res.get("account_number", parent_affiliate.get("account_number", "")),
                            "scheduled_at": now,
                            "status": "pending",
                            "retry_count": 0,
                            "sent_at": None,
                            "error": None,
                        })
                    except DuplicateKeyError:
                        pass

    if direct_triggered or parent_triggered:
        from ..workers.email_scheduler import process_email_queue
        import asyncio
        asyncio.create_task(process_email_queue())

    return {
        "direct_milestone_triggered": direct_triggered,
        "parent_milestone_triggered": parent_triggered,
        "sales_count": sales_count,
    }



async def get_affiliate_recruits_and_bonuses(db, affiliate_code: str) -> dict:
    """
    Fetch all invited affiliates and unlocked milestone bonuses for a given affiliate.
    """
    if not affiliate_code or db is None:
        return {
            "invited_affiliates": [],
            "milestones": [],
            "total_bonus_unlocked": 0.0,
            "total_bonus_paid": 0.0,
            "total_recruits": 0,
        }

    # 1. Fetch invited affiliates
    recruits_cursor = db.affiliates.find({"invited_by": affiliate_code}).sort("created_at", -1)
    recruits = await recruits_cursor.to_list(1000)

    # Aggregate sales for all recruits
    recruit_codes = [r["code"] for r in recruits]
    sales_by_code = {}
    if recruit_codes:
        pipeline = [
            {"$match": {"affiliate_code": {"$in": recruit_codes}}},
            {"$group": {"_id": "$affiliate_code", "count": {"$sum": 1}}},
        ]
        async for row in db.referrals.aggregate(pipeline):
            sales_by_code[row["_id"]] = row["count"]

    invited_list = []
    for r in recruits:
        code = r["code"]
        count = sales_by_code.get(code, 0)
        target = MILESTONE_SALES_TARGET
        percent = min(100, round((count / target) * 100, 1))
        invited_list.append({
            "code": code,
            "name": r.get("name", ""),
            "created_at": r.get("created_at"),
            "sales_count": count,
            "target": target,
            "progress_percent": percent,
            "bonus_unlocked": count >= target,
            "bonus_amount": PARENT_RECRUITER_BONUS if count >= target else 0.0,
        })

    # 2. Fetch milestone records
    milestones = await db.affiliate_milestones.find({
        "affiliate_code": affiliate_code
    }).sort("created_at", -1).to_list(100)

    total_bonus_unlocked = sum(m.get("amount", 0) for m in milestones)
    total_bonus_paid = sum(m.get("amount", 0) for m in milestones if m.get("status") == "paid")

    formatted_milestones = [
        {
            "type": m.get("type"),
            "amount": m.get("amount", 0),
            "description": m.get("description", ""),
            "status": m.get("status", "unlocked"),
            "created_at": m.get("created_at"),
            "paid_at": m.get("paid_at"),
            "subaffiliate_name": m.get("subaffiliate_name"),
        }
        for m in milestones
    ]

    return {
        "invited_affiliates": invited_list,
        "milestones": formatted_milestones,
        "total_bonus_unlocked": total_bonus_unlocked,
        "total_bonus_paid": total_bonus_paid,
        "total_recruits": len(recruits),
    }
