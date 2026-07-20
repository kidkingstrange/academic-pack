"""
Admin-only email delivery tracking — read-only queries against
email_queue, surfaced proactively instead of requiring a manual DB
query to notice a problem (see services/email_delivery_service.py for
the "why" behind this feature).
"""
from fastapi import APIRouter, Depends

from ..database import get_db
from ..middleware.auth import require_admin
from ..services.email_delivery_service import get_overview, list_by_status, get_customer_timeline

router = APIRouter(prefix="/api/admin/email-delivery", tags=["admin-email-delivery"])


@router.get("/overview")
async def email_delivery_overview(current_user=Depends(require_admin), db=Depends(get_db)):
    return await get_overview(db)


@router.get("/failed")
async def email_delivery_failed(page: int = 1, limit: int = 50, current_user=Depends(require_admin), db=Depends(get_db)):
    return await list_by_status(db, "failed", page=page, limit=limit)


@router.get("/retrying")
async def email_delivery_retrying(page: int = 1, limit: int = 50, current_user=Depends(require_admin), db=Depends(get_db)):
    return await list_by_status(db, "retry", page=page, limit=limit)


@router.get("/customer")
async def email_delivery_customer(query: str = "", page: int = 1, limit: int = 50, current_user=Depends(require_admin), db=Depends(get_db)):
    return await get_customer_timeline(db, query, page=page, limit=limit)
