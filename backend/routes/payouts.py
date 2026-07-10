"""
Admin-only payout routes. Batch generation runs on a schedule (see
workers/email_scheduler.py) but can also be triggered manually here for
testing or an out-of-cycle run. Confirmation is the one human checkpoint
that actually moves money — see services/payout_service.py.
"""
from fastapi import APIRouter, Depends, HTTPException

from ..middleware.auth import require_admin
from ..database import get_db
from ..services.payout_service import generate_weekly_payout_batch, confirm_payout_batch

router = APIRouter(prefix="/api/admin/payouts", tags=["payouts"])


def _mask_account_number(account_number: str) -> str:
    if not account_number or len(account_number) < 4:
        return "••••"
    return f"•••• {account_number[-4:]}"


@router.post("/generate-batch")
async def trigger_batch_generation(current_user=Depends(require_admin), db=Depends(get_db)):
    batch = await generate_weekly_payout_batch(db)
    if not batch:
        return {"created": False, "message": "No unpaid conversions — no batch generated."}
    return {"created": True, "batch_id": batch["batch_id"], "total_amount": batch["total_amount"], "line_item_count": len(batch["line_items"])}


@router.get("/batches")
async def list_batches(current_user=Depends(require_admin), db=Depends(get_db)):
    batches = await db.payout_batches.find({}).sort("created_at", -1).to_list(100)
    out = []
    for b in batches:
        line_items = [
            {**item, "bank_account_number": _mask_account_number(item.get("bank_account_number"))}
            for item in b["line_items"]
        ]
        out.append({
            "batch_id": b["batch_id"],
            "created_at": b["created_at"],
            "status": b["status"],
            "total_amount": b["total_amount"],
            "line_items": line_items,
            "confirmed_at": b.get("confirmed_at"),
            "confirmed_by": b.get("confirmed_by"),
        })
    return {"batches": out}


@router.post("/{batch_id}/confirm")
async def confirm_batch(batch_id: str, current_user=Depends(require_admin), db=Depends(get_db)):
    try:
        result = await confirm_payout_batch(db, batch_id, confirmed_by=current_user.get("email", "admin"))
    except ValueError as e:
        reason = str(e)
        if reason == "batch_not_found":
            raise HTTPException(status_code=404, detail="Batch not found")
        raise HTTPException(status_code=409, detail=reason.replace("_", " "))
    return result
