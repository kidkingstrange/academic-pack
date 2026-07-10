"""
FastAPI application entry point.
Run with: uvicorn backend.main:app --reload --port 8000
"""
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, RedirectResponse
from pathlib import Path
from bson import ObjectId
from pymongo import ReturnDocument
from datetime import datetime, timezone
import time
from starlette.responses import Response
from starlette.types import Scope

from .config import get_settings
from .database import connect_db, disconnect_db, get_db
from .routes import payments, library, admin as admin_router, community, affiliates, affiliate_public, payouts
from .workers.email_scheduler import start_scheduler, stop_scheduler
from .utils.security import create_access_token
from .utils.error_pages import expired_link_page
from .middleware.auth import require_admin

settings = get_settings()

app = FastAPI(
    title="Academic Comeback API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ── Compression ───────────────────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Security Headers Middleware ────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ── Request Timing ────────────────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.time() - start)
    return response

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(payments.router)
app.include_router(library.router)
app.include_router(admin_router.router)
app.include_router(community.router)
app.include_router(affiliates.router)
app.include_router(affiliate_public.router)
app.include_router(payouts.router)

# ── Static Files (Frontend) ───────────────────────────────────────────────────
class CachedStaticFiles(StaticFiles):
    def __init__(self, *args, cache_control: str = "public, max-age=86400", **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_control = cache_control

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = self.cache_control
        return response

frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/assets", CachedStaticFiles(directory=str(frontend_path / "assets"), cache_control="public, max-age=86400"), name="assets")
    app.mount("/css", CachedStaticFiles(directory=str(frontend_path / "css"), cache_control="public, max-age=3600"), name="css")
    app.mount("/js", CachedStaticFiles(directory=str(frontend_path / "js"), cache_control="public, max-age=3600"), name="js")

# ── SPA-style Page Routes ─────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(str(frontend_path / "index.html"))

@app.get("/welcome", include_in_schema=False)
async def serve_welcome():
    return FileResponse(str(frontend_path / "welcome.html"))

@app.get("/library", include_in_schema=False)
async def serve_library():
    return FileResponse(str(frontend_path / "library.html"))

@app.get("/access", include_in_schema=False)
async def serve_access():
    # Click-gated intermediate landing page — see frontend/access.html for why.
    return FileResponse(str(frontend_path / "access.html"))

@app.get("/affiliate/register", include_in_schema=False)
async def serve_affiliate_register():
    return FileResponse(str(frontend_path / "affiliate-register.html"))

@app.get("/r/{code}", include_in_schema=False)
async def track_referral(code: str, request: Request, db=Depends(get_db)):
    """Affiliate referral link — logs the click, then redirects into the
    normal landing-page flow with ?ref= so checkout can attach it later."""
    normalized = code.strip().upper()
    affiliate = await db.affiliates.find_one({"code": normalized, "active": True})
    if affiliate:
        await db.referral_clicks.insert_one({
            "affiliate_code": normalized,
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "referrer": request.headers.get("referer", ""),
            "created_at": datetime.now(timezone.utc),
        })
        return RedirectResponse(url=f"/?ref={normalized}")
    # Unknown/inactive code — fail gracefully, no error shown to the visitor.
    return RedirectResponse(url="/")

@app.get("/api/_debug/flw-diagnostic", include_in_schema=False)
async def flw_diagnostic(current_user=Depends(require_admin)):
    """
    TEMPORARY, admin-gated — systematic diagnosis of the sandbox
    /customers 403. Reveals credential SHAPE (length, edges, whitespace)
    never the raw secret values, and returns FLW's real responses for
    /banks and /customers side by side so we can tell whether the 403
    is specific to /customers or affects the whole sandbox account.
    Remove after the investigation concludes — not meant to ship
    long-term. Gated behind require_admin since it returns partial
    credential shape + raw upstream API responses.
    """
    import base64
    import json as jsonlib
    import uuid as uuidlib
    import httpx
    from .services.flutterwave import FLW_API_BASE, FLW_AUTH_URL

    report = {}

    report["client_id_len"] = len(settings.FLW_CLIENT_ID)
    report["client_id_edges"] = f"{settings.FLW_CLIENT_ID[:4]}...{settings.FLW_CLIENT_ID[-4:]}" if len(settings.FLW_CLIENT_ID) >= 8 else "too short"
    report["client_id_has_whitespace"] = settings.FLW_CLIENT_ID != settings.FLW_CLIENT_ID.strip()
    report["client_secret_len"] = len(settings.FLW_CLIENT_SECRET)
    report["client_secret_has_whitespace"] = settings.FLW_CLIENT_SECRET != settings.FLW_CLIENT_SECRET.strip()

    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                FLW_AUTH_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_id": settings.FLW_CLIENT_ID,
                    "client_secret": settings.FLW_CLIENT_SECRET,
                    "grant_type": "client_credentials",
                },
                timeout=15,
            )
        token_data = token_resp.json()
        report["token_status_code"] = token_resp.status_code
        # Top-level OAuth response fields — NOT the raw access_token itself.
        report["token_response_fields"] = {k: v for k, v in token_data.items() if k != "access_token"}
        token = token_data.get("access_token")
        report["token_acquired"] = bool(token)
        if token:
            parts = token.split(".")
            if len(parts) == 3:
                payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
                payload = jsonlib.loads(base64.urlsafe_b64decode(payload_b64))
                safe_keys = {"scope", "aud", "iss", "azp", "exp", "iat", "typ", "environment", "mode", "realm_access", "resource_access", "allowed-origins"}
                report["token_jwt_claims"] = {k: v for k, v in payload.items() if k in safe_keys}
            else:
                report["token_jwt_claims"] = "not a 3-part JWT — opaque token, cannot inspect claims"
        else:
            return report
    except Exception as e:
        report["token_acquired"] = False
        report["token_error"] = str(e)
        return report

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{FLW_API_BASE}/banks",
                headers={"Authorization": f"Bearer {token}", "X-Trace-Id": str(uuidlib.uuid4())},
                params={"country": "NG"},
                timeout=15,
            )
            report["banks_status_code"] = resp.status_code
            report["banks_response"] = resp.json()
    except Exception as e:
        report["banks_error"] = str(e)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{FLW_API_BASE}/customers",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Trace-Id": str(uuidlib.uuid4()),
                },
                json={"email": "flw-diagnostic-test@example.com", "name": {"first": "Diagnostic", "last": "Test"}},
                timeout=15,
            )
            report["customers_full_body_status_code"] = resp.status_code
            report["customers_full_body_response"] = resp.json()
    except Exception as e:
        report["customers_full_body_error"] = str(e)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{FLW_API_BASE}/customers",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Trace-Id": str(uuidlib.uuid4()),
                },
                json={"email": "flw-diagnostic-test2@example.com"},
                timeout=15,
            )
            report["customers_minimal_body_status_code"] = resp.status_code
            report["customers_minimal_body_response"] = resp.json()
    except Exception as e:
        report["customers_minimal_body_error"] = str(e)

    return report

@app.get("/verification-pending.html", include_in_schema=False)
async def serve_verification_pending():
    # exchange_magic_token()'s "new device/browser" branch redirects here.
    # The file existed and was committed, but never had a route — any real
    # hit to that branch 404'd instead of showing the "check your email"
    # message.
    return FileResponse(str(frontend_path / "verification-pending.html"))

@app.get("/admin", include_in_schema=False)
async def serve_admin():
    return FileResponse(str(frontend_path / "admin" / "index.html"))

@app.get("/admin/dashboard", include_in_schema=False)
async def serve_dashboard():
    return FileResponse(str(frontend_path / "admin" / "dashboard.html"))

# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}

@app.get("/api/auth/magic", include_in_schema=True)
async def exchange_magic_token(
    request: Request,
    response: Response,
    token: str = "",
    redirect: str = "/welcome",
    db=Depends(get_db)
):
    """
    Exchange a reusable magic token for a session cookie and JWT.
    Binds the magic link to a browser session on first use.
    If accessed from a new device/browser, triggers a fresh email re-verification step.
    """
    import secrets
    import hashlib
    from datetime import timedelta
    from backend.services.email_service import send_welcome_email

    if not token:
        raise HTTPException(status_code=400, detail="Missing magic token")

    now = datetime.now(timezone.utc)

    # 1. Look up magic link in the database (active for 90 days, used check removed to support reuse)
    magic_link = await db.magic_links.find_one({
        "token": token,
        "expires_at": {"$gt": now}
    })

    if not magic_link:
        return expired_link_page(
            "This link is invalid or has expired. If you haven't accessed your library yet, "
            "check your welcome email for the correct link, or contact support.",
            heading="Link expired",
            cta_text="Go to Homepage",
            cta_href="/",
        )

    user_id = str(magic_link["user_id"])
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    email = user["email"]
    role = user.get("role", "customer")

    # Log access for anomaly visibility
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    print(f"🔒 Magic link access: token={token}, user={email}, IP={client_ip}, UA={user_agent}, time={now}")

    # 2. Check if browser already has a valid session cookie
    session_cookie = request.cookies.get("ac_session")
    session_verified = False
    session_id = None

    if session_cookie:
        h = hashlib.sha256(session_cookie.encode()).hexdigest()
        existing_session = await db.sessions.find_one({
            "session_hash": h,
            "magic_token": token,
            "expires_at": {"$gt": now}
        })
        if existing_session:
            session_verified = True
            session_id = session_cookie

    if not session_verified:
        # Check if this magic token has been used to create an active session on any other device/browser
        other_active_session = await db.sessions.find_one({
            "magic_token": token,
            "expires_at": {"$gt": now}
        })

        if other_active_session:
            print(f"⚠️ Re-verification triggered: magic link {token} accessed from a new device/browser.")
            
            # Generate a new magic link token
            new_magic_token = secrets.token_urlsafe(32)
            await db.magic_links.insert_one({
                "token": new_magic_token,
                "user_id": ObjectId(user_id),
                "purpose": "welcome",
                "expires_at": now + timedelta(days=90),
                "used": False,
                "created_at": now
            })

            # Retrieve unsubscribe token
            sub = await db.subscribers.find_one({"email": email.lower()})
            unsub_token = sub.get("unsubscribe_token", "") if sub else ""

            # Resend new magic link email
            await send_welcome_email(user["name"], email.lower(), new_magic_token, unsub_token)
            
            # Redirect to the verification pending page
            return RedirectResponse(url="/verification-pending.html")

        # First use -> Create a new session and bind the cookie!
        session_id = secrets.token_urlsafe(32)
        session_hash = hashlib.sha256(session_id.encode()).hexdigest()
        
        await db.sessions.insert_one({
            "session_hash": session_hash,
            "user_id": ObjectId(user_id),
            "magic_token": token,
            "ip_address": client_ip,
            "user_agent": user_agent,
            "created_at": now,
            "expires_at": now + timedelta(days=90)
        })

    # 3. Create access token for frontend compatibility (sessionStorage fallback)
    session_token = create_access_token({"sub": user_id, "email": email, "role": role})

    if redirect not in ["/welcome", "/library"]:
        redirect = "/welcome"

    redirect_target = f"{redirect}#token={session_token}"
    redirect_resp = RedirectResponse(url=redirect_target)
    
    # Always set/refresh session cookie on response if we have a valid session_id
    if session_id:
        redirect_resp.set_cookie(
            key="ac_session",
            value=session_id,
            max_age=90 * 24 * 3600,
            expires=90 * 24 * 3600,
            path="/",
            httponly=True,
            secure=True if settings.APP_ENV == "production" else False,
            samesite="lax"
        )
    return redirect_resp

@app.get("/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
async def unsubscribe(token: str = "", db=Depends(get_db)):
    """
    Unsubscribe from all email sequences using unsubscribe token.
    Generic response returned for both valid and invalid tokens.
    """
    if db is not None and token:
        await db.subscribers.update_one(
            {"unsubscribe_token": token},
            {"$set": {"is_active": False}}
        )

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unsubscribed — Academic Comeback</title>
    <style>
        body {
            background-color: #0d0f14;
            color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            text-align: center;
        }
        .container {
            max-width: 480px;
            padding: 40px 24px;
            background: linear-gradient(135deg, #161922, #0d0f14);
            border-radius: 16px;
            border: 1px solid rgba(212, 166, 58, 0.15);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }
        .icon {
            font-size: 3rem;
            color: #d4a63a;
            margin-bottom: 20px;
        }
        h1 {
            font-size: 1.8rem;
            margin: 0 0 12px 0;
            font-weight: 700;
        }
        p {
            color: #aaa;
            font-size: 1rem;
            line-height: 1.6;
            margin: 0 0 24px 0;
        }
        .btn {
            display: inline-block;
            background: linear-gradient(135deg, #d4a63a, #e8bf5a);
            color: #0d0f14;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 50px;
            font-weight: 700;
            font-size: 0.9rem;
            transition: opacity 0.2s;
        }
        .btn:hover {
            opacity: 0.9;
        }
    </style>
    </head>
    <body>
    <div class="container">
        <div class="icon">✓</div>
        <h1>You've been unsubscribed</h1>
        <p>We've removed your email address from our automated learning sequence. You will no longer receive these curriculum emails.</p>
        <a href="/" class="btn">Return Home</a>
    </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await connect_db()
    start_scheduler()
    print(f"🚀 {settings.APP_NAME} API started")

@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()
    await disconnect_db()
