"""
Authentication, account activation, and password management for affiliates.
Allows existing and new affiliates to activate their accounts, establish passwords,
and log in securely with JWT sessions while preserving all existing affiliate data.
"""
import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from bson import ObjectId

from ..config import get_settings
from ..database import get_db
from ..middleware.auth import get_current_user, require_affiliate
from ..schemas.schemas import (
    AffiliateActivationRequest,
    AffiliateSetPasswordRequest,
    AffiliateLoginRequest,
    AffiliateForgotPasswordRequest,
    AffiliateResetPasswordRequest,
)
from ..utils.rate_limit import limiter
from ..utils.security import hash_password, verify_password, create_access_token
from ..workers.email_scheduler import process_email_queue

router = APIRouter(prefix="/api/affiliate/auth", tags=["affiliate-auth"])
settings = get_settings()

TOKEN_EXPIRY_MINUTES = 60


def _hash_token(raw_token: str) -> str:
    """SHA-256 hash of single-use URL tokens to prevent plaintext token storage in DB."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


# ── 1. Account Activation ───────────────────────────────────────────────────

@router.post("/activate/request")
@limiter.limit("5/minute")
async def request_account_activation(
    request: Request,
    body: AffiliateActivationRequest,
    db=Depends(get_db)
):
    """
    Request an account activation link for an existing affiliate.
    Enumeration-safe: always returns generic success message regardless of
    whether the email is in db.affiliates.
    """
    email = body.email.strip().lower()
    now = datetime.now(timezone.utc)

    affiliate = await db.affiliates.find_one({"email": email})
    if affiliate and affiliate.get("active", True):
        # Generate high-entropy single-use token and store its SHA-256 hash
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = now + timedelta(minutes=TOKEN_EXPIRY_MINUTES)

        await db.affiliates.update_one(
            {"_id": affiliate["_id"]},
            {"$set": {
                "activation_token_hash": token_hash,
                "activation_token_expires_at": expires_at,
            }}
        )

        activation_link = f"{settings.APP_URL}/affiliate/activate?token={raw_token}"

        await db.email_queue.insert_one({
            "kind": "affiliate_activation",
            "email": affiliate["email"],
            "name": affiliate["name"],
            "code": affiliate["code"],
            "activation_link": activation_link,
            "scheduled_at": now,
            "status": "pending",
            "retry_count": 0,
            "sent_at": None,
            "error": None,
        })
        asyncio.create_task(process_email_queue())

    # Generic enumeration-safe response
    return {
        "status": "success",
        "message": "If an affiliate account exists for this email, you will receive an account activation link shortly."
    }


@router.get("/activate/verify")
async def verify_activation_token(token: str, db=Depends(get_db)):
    """
    Validates an activation token when the user lands on /affiliate/activate?token=...
    Returns affiliate email and name so the UI can prefill/show the user identity.
    """
    clean_token = token.strip()
    if not clean_token:
        raise HTTPException(status_code=400, detail="Activation token is missing.")

    token_hash = _hash_token(clean_token)
    affiliate = await db.affiliates.find_one({"activation_token_hash": token_hash})

    if not affiliate:
        raise HTTPException(status_code=400, detail="Invalid or already used activation link.")

    expires_at = affiliate.get("activation_token_expires_at")
    if not expires_at:
        raise HTTPException(status_code=400, detail="Activation link is invalid or expired.")

    # Ensure tz-aware comparison
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="This activation link has expired. Please request a new one.")

    return {
        "valid": True,
        "email": affiliate["email"],
        "name": affiliate["name"],
        "code": affiliate["code"],
    }


@router.post("/activate/confirm")
@limiter.limit("5/minute")
async def confirm_account_activation(
    request: Request,
    body: AffiliateSetPasswordRequest,
    db=Depends(get_db)
):
    """
    Completes account activation:
    1. Validates single-use token and expiration.
    2. Hashes password using bcrypt.
    3. Marks account as activated.
    4. Invalidates the token immediately.
    5. Returns JWT access token and dashboard token for immediate login.
    """
    clean_token = body.token.strip()
    token_hash = _hash_token(clean_token)
    affiliate = await db.affiliates.find_one({"activation_token_hash": token_hash})

    if not affiliate:
        raise HTTPException(status_code=400, detail="Invalid or already used activation link.")

    expires_at = affiliate.get("activation_token_expires_at")
    if not expires_at:
        raise HTTPException(status_code=400, detail="Activation link is invalid or expired.")

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="This activation link has expired. Please request a new one.")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    password_hash = hash_password(body.password)
    now = datetime.now(timezone.utc)

    # Invalidate token immediately and record activation
    await db.affiliates.update_one(
        {"_id": affiliate["_id"]},
        {
            "$set": {
                "password_hash": password_hash,
                "account_activated": True,
                "activated_at": now,
                "last_login": now,
            },
            "$unset": {
                "activation_token_hash": "",
                "activation_token_expires_at": "",
            }
        }
    )

    # Issue JWT session token
    access_token = create_access_token({
        "sub": str(affiliate["_id"]),
        "email": affiliate["email"],
        "role": "affiliate",
    })

    return {
        "status": "success",
        "message": "Account activated successfully!",
        "access_token": access_token,
        "token_type": "bearer",
        "dashboard_token": affiliate.get("dashboard_token"),
        "code": affiliate["code"],
        "name": affiliate["name"],
        "email": affiliate["email"],
    }


# ── 2. Affiliate Login ──────────────────────────────────────────────────────

@router.post("/login")
@limiter.limit("10/minute")
async def affiliate_login(
    request: Request,
    body: AffiliateLoginRequest,
    db=Depends(get_db)
):
    """
    Standard login for activated affiliates using email and password.
    Returns JWT session token and dashboard token.
    If the account exists but has not set a password, returns a helpful message
    guiding them to activate.
    """
    email = body.email.strip().lower()
    affiliate = await db.affiliates.find_one({"email": email})

    if not affiliate or not affiliate.get("active", True):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    pwd_hash = affiliate.get("password_hash")
    is_activated = affiliate.get("account_activated", False)

    # Check if the account has never been activated / has no password
    if not pwd_hash or not is_activated:
        raise HTTPException(
            status_code=403,
            detail="Your affiliate account exists but has not been activated yet. Please activate your account first to set a password.",
            headers={"X-Needs-Activation": "true"}
        )

    if not verify_password(body.password, pwd_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    now = datetime.now(timezone.utc)
    await db.affiliates.update_one(
        {"_id": affiliate["_id"]},
        {"$set": {"last_login": now}}
    )

    expires_delta = timedelta(days=30) if body.remember_me else timedelta(days=settings.JWT_EXPIRE_DAYS)
    access_token = create_access_token(
        {
            "sub": str(affiliate["_id"]),
            "email": affiliate["email"],
            "role": "affiliate",
        },
        expires_delta=expires_delta,
    )

    return {
        "status": "success",
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "dashboard_token": affiliate.get("dashboard_token"),
        "code": affiliate["code"],
        "name": affiliate["name"],
        "email": affiliate["email"],
    }


# ── 3. Forgot Password Flow ─────────────────────────────────────────────────

@router.post("/forgot-password/request")
@limiter.limit("5/minute")
async def request_password_reset(
    request: Request,
    body: AffiliateForgotPasswordRequest,
    db=Depends(get_db)
):
    """
    Request password reset link. Enumeration-safe.
    """
    email = body.email.strip().lower()
    now = datetime.now(timezone.utc)

    affiliate = await db.affiliates.find_one({"email": email})
    if affiliate and affiliate.get("active", True):
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = now + timedelta(minutes=TOKEN_EXPIRY_MINUTES)

        await db.affiliates.update_one(
            {"_id": affiliate["_id"]},
            {"$set": {
                "reset_token_hash": token_hash,
                "reset_token_expires_at": expires_at,
            }}
        )

        reset_link = f"{settings.APP_URL}/affiliate/activate?mode=reset&token={raw_token}"

        await db.email_queue.insert_one({
            "kind": "affiliate_password_reset",
            "email": affiliate["email"],
            "name": affiliate["name"],
            "reset_link": reset_link,
            "scheduled_at": now,
            "status": "pending",
            "retry_count": 0,
            "sent_at": None,
            "error": None,
        })
        asyncio.create_task(process_email_queue())

    return {
        "status": "success",
        "message": "If an affiliate account exists for this email, you will receive a password reset link shortly."
    }


@router.get("/forgot-password/verify")
async def verify_password_reset_token(token: str, db=Depends(get_db)):
    """
    Validates a password reset token before showing the reset form.
    """
    clean_token = token.strip()
    if not clean_token:
        raise HTTPException(status_code=400, detail="Reset token is missing.")

    token_hash = _hash_token(clean_token)
    affiliate = await db.affiliates.find_one({"reset_token_hash": token_hash})

    if not affiliate:
        raise HTTPException(status_code=400, detail="Invalid or already used password reset link.")

    expires_at = affiliate.get("reset_token_expires_at")
    if not expires_at:
        raise HTTPException(status_code=400, detail="Password reset link is invalid or expired.")

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="This password reset link has expired. Please request a new one.")

    return {
        "valid": True,
        "email": affiliate["email"],
        "name": affiliate["name"],
    }


@router.post("/forgot-password/confirm")
@limiter.limit("5/minute")
async def confirm_password_reset(
    request: Request,
    body: AffiliateResetPasswordRequest,
    db=Depends(get_db)
):
    """
    Confirms password reset, updates password_hash, clears token, and returns success.
    """
    clean_token = body.token.strip()
    token_hash = _hash_token(clean_token)
    affiliate = await db.affiliates.find_one({"reset_token_hash": token_hash})

    if not affiliate:
        raise HTTPException(status_code=400, detail="Invalid or already used password reset link.")

    expires_at = affiliate.get("reset_token_expires_at")
    if not expires_at:
        raise HTTPException(status_code=400, detail="Password reset link is invalid or expired.")

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="This password reset link has expired. Please request a new one.")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    password_hash = hash_password(body.password)
    now = datetime.now(timezone.utc)

    await db.affiliates.update_one(
        {"_id": affiliate["_id"]},
        {
            "$set": {
                "password_hash": password_hash,
                "account_activated": True,
                "password_reset_at": now,
            },
            "$unset": {
                "reset_token_hash": "",
                "reset_token_expires_at": "",
            }
        }
    )

    return {
        "status": "success",
        "message": "Your password has been reset successfully. You can now log in.",
    }


# ── 4. Current Affiliate Profile ─────────────────────────────────────────────

@router.get("/me")
async def get_current_affiliate_profile(
    current_user=Depends(require_affiliate),
    db=Depends(get_db)
):
    """
    Returns the authenticated affiliate's identity using their JWT session.
    """
    oid = ObjectId(current_user["user_id"])
    affiliate = await db.affiliates.find_one({"_id": oid})
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate profile not found")

    return {
        "id": str(affiliate["_id"]),
        "name": affiliate["name"],
        "email": affiliate["email"],
        "code": affiliate["code"],
        "dashboard_token": affiliate.get("dashboard_token"),
        "account_activated": affiliate.get("account_activated", False),
    }
