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
from .routes import (
    payments, library, admin as admin_router, community,
    affiliates, affiliate_public, affiliate_dashboard, tracking,
)
from .workers.email_scheduler import start_scheduler, stop_scheduler
from .utils.security import create_access_token
from .utils.error_pages import expired_link_page

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
app.include_router(affiliate_dashboard.router)
app.include_router(tracking.router)
# admin_analytics.router intentionally NOT wired up — it duplicates the
# /api/admin/analytics/* endpoints now built directly in routes/admin.py,
# and additionally bakes in a tier-badge system, a ranked leaderboard,
# hardcoded fake AI-insight text, and some hardcoded placeholder numbers
# (avg_cart_value, upsell_rate) — all explicitly out of scope. Left as a
# dormant file rather than deleted, pending an explicit call on whether to
# remove it entirely.

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

@app.get("/admin", include_in_schema=False)
async def serve_admin():
    return FileResponse(
        str(frontend_path / "admin" / "index.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.get("/admin/dashboard", include_in_schema=False)
async def serve_dashboard():
    return FileResponse(
        str(frontend_path / "admin" / "dashboard.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.get("/affiliate/register", include_in_schema=False)
async def serve_affiliate_register():
    return FileResponse(
        str(frontend_path / "affiliate-register.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.get("/affiliate/dashboard", include_in_schema=False)
async def serve_affiliate_dashboard():
    return FileResponse(
        str(frontend_path / "affiliate-dashboard.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.get("/r/{code}", include_in_schema=False)
async def track_referral(code: str, request: Request, db=Depends(get_db)):
    """
    Affiliate referral link — logs the click, then redirects into the
    normal landing-page flow with ?ref= so checkout can attach it later.
    Unknown/inactive codes fail gracefully to the homepage with no error
    shown to the visitor — attribution is a nice-to-have, never a gate.
    """
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
        return RedirectResponse(url=f"/?ref={normalized}&price=5000")
    return RedirectResponse(url="/")

# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


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
