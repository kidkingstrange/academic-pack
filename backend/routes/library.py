"""
Protected library routes — requires valid library access token.
"""
import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from ..utils.security import create_download_token, verify_token
from ..utils.error_pages import expired_link_page
from ..database import get_db
from ..config import get_settings

router = APIRouter(prefix="/api/library", tags=["library"])
settings = get_settings()
security = HTTPBearer(auto_error=False)


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

    # Check if this token has already been used
    already_used = await db.used_tokens.find_one({"jti": jti})
    if already_used:
        return expired_link_page(
            "This link has already been used. If you haven't downloaded this book yet, return "
            "to your library and click Download again for a fresh link.",
            heading="Link already used",
        )

    # Mark token as used immediately before serving the file
    await db.used_tokens.insert_one({
        "jti": jti,
        "used_at": datetime.now(timezone.utc)
    })

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
