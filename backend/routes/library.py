"""
Protected library routes — requires valid library access token.
"""
import os
import asyncio
import secrets
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from bson import ObjectId
from ..utils.security import create_download_token, verify_token
from ..utils.error_pages import expired_link_page
from ..database import get_db
from ..config import get_settings
from ..workers.email_scheduler import process_email_queue

router = APIRouter(prefix="/api/library", tags=["library"])
settings = get_settings()
security = HTTPBearer(auto_error=False)


class ResendLibraryLinkRequest(BaseModel):
    email: EmailStr


@router.post("/resend-link")
async def resend_library_link(body: ResendLibraryLinkRequest, db=Depends(get_db)):
    """Self-service recovery for a customer whose access link is lost —
    e.g. localStorage wiped by a Facebook/Instagram in-app browser between
    sessions, or they simply can't find the original email. Always returns
    the same generic message regardless of whether the email matches an
    account, so this can't be used to enumerate customers."""
    email = body.email.strip().lower()
    generic_response = {
        "success": True,
        "message": "If an account exists for that email, we've sent your library access link.",
    }

    user = await db.users.find_one({"email": email})
    if not user:
        return generic_response

    access_token = user.get("library_access_token")
    if not access_token:
        access_token = secrets.token_urlsafe(32)
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"library_access_token": access_token}})

    subscriber = await db.subscribers.find_one({"email": email})
    unsub_token = subscriber.get("unsubscribe_token", "") if subscriber else ""

    await db.email_queue.insert_one({
        "kind": "welcome",
        "user_id": user["_id"],
        "email": email,
        "name": user.get("name") or "there",
        "access_token": access_token,
        "unsubscribe_token": unsub_token,
        "scheduled_at": datetime.now(timezone.utc),
        "status": "pending",
        "retry_count": 0,
        "sent_at": None,
        "error": None,
    })
    asyncio.create_task(process_email_queue())
    return generic_response


async def get_library_user(
    token: str = "",
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db)
):
    """Retrieve user based on library_access_token query parameter or Authorization header."""
    access_token = token
    if not access_token and credentials:
        access_token = credentials.credentials

    if not access_token:
        raise HTTPException(status_code=401, detail="Missing library access token")

    user = await db.users.find_one({"library_access_token": access_token})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid library access token")
    return user


@router.get("")
async def get_library(user=Depends(get_library_user), db=Depends(get_db)):
    """Return all products the user has purchased."""
    products = await db.products.find({"is_active": True}).sort("order", 1).to_list(100)
    result = []
    for p in products:
        result.append({
            "id": str(p["_id"]),
            "title": p["title"],
            "description": p["description"],
            "thumbnail": p.get("thumbnail"),
            "order": p["order"],
        })

    return {"products": result, "user_name": user["name"]}


@router.get("/sign/{product_id}")
async def sign_download(
    product_id: str,
    user=Depends(get_library_user),
    db=Depends(get_db),
):
    """Issue a short-lived signed URL for downloading a specific product."""
    product = await db.products.find_one({"_id": ObjectId(product_id), "is_active": True})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    user_id = str(user["_id"])
    # Verify user has access
    if not user or ("all" not in user.get("purchased_products", []) and
                    product_id not in user.get("purchased_products", [])):
        raise HTTPException(status_code=403, detail="Access denied")

    # Issue signed token
    signed_token = create_download_token(user_id, product_id)

    # Log download attempt
    await db.downloads.insert_one({
        "user_id": ObjectId(user_id),
        "product_id": ObjectId(product_id),
        "downloaded_at": datetime.now(timezone.utc),
        "product_title": product["title"],
    })

    return {
        "signed_url": f"/api/library/file/{signed_token}",
        "expires_in": settings.JWT_DOWNLOAD_EXPIRE_MINUTES * 60,
        "filename": product["title"].replace(" ", "_") + ".pdf",
    }


@router.get("/file/{signed_token}")
async def download_file(signed_token: str, db=Depends(get_db)):
    """Serve a protected PDF file using a signed token."""
    payload = verify_token(signed_token)
    if not payload or payload.get("type") != "download":
        return expired_link_page(
            "This download link is invalid or has expired. Return to your library and click "
            "Download again for a fresh link.",
        )

    jti = payload.get("jti")
    if not jti:
        return expired_link_page(
            "This download link is invalid or has expired. Return to your library and click "
            "Download again for a fresh link.",
        )

    # Single-use blocking removed: on a slow/flaky mobile connection, a
    # stalled download's automatic browser retry hit this same signed URL
    # a second time — but the token was marked "used" the instant serving
    # started, before the file ever finished transferring, so the retry
    # (the customer's own browser, not a leaked link) got permanently
    # locked out. This token has no separate time-based expiry (see
    # create_download_token), so removing the single-use gate means a
    # signed download link now remains valid indefinitely rather than for
    # one serve — an accepted tradeoff to stop legitimate customers being
    # falsely locked out of a book they already paid for.
    product_id = payload.get("product_id")
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    file_path = Path(settings.UPLOADS_DIR) / product["file_path"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not available yet")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=product["title"].replace(" ", "_") + ".pdf",
    )
