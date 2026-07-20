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

from .config import get_settings, DEFAULT_ADMIN_PASSWORD
from .database import connect_db, disconnect_db, get_db
from .routes import (
    payments, library, admin as admin_router, community,
    affiliates, affiliate_public, affiliate_dashboard, tracking,
    admin_payouts, sales as sales_router, admin_email_delivery,
)
from .workers.email_scheduler import start_scheduler, stop_scheduler
from .workers.payout_scheduler import start_payout_scheduler, stop_payout_scheduler
from .workers.affiliate_nudge_scheduler import start_nudge_scheduler, stop_nudge_scheduler
from .workers.subscription_scheduler import start_subscription_scheduler, stop_subscription_scheduler
from .workers.email_delivery_alert_scheduler import start_alert_scheduler, stop_alert_scheduler
from .utils.security import create_access_token
from .utils.error_pages import expired_link_page
from .utils.rate_limit import limiter, get_real_client_ip
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

settings = get_settings()

app = FastAPI(
    title="Academic Comeback API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
# slowapi was already a pinned dependency but never actually wired in —
# login, checkout, and registration endpoints had no abuse/brute-force
# throttling of any kind.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(admin_payouts.router)
app.include_router(sales_router.router)
app.include_router(admin_email_delivery.router)
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

# ── SEO / crawler files ────────────────────────────────────────────────────────
@app.get("/favicon.ico", include_in_schema=False)
async def serve_favicon():
    return FileResponse(str(frontend_path / "favicon.ico"), headers={"Cache-Control": "public, max-age=86400"})

@app.get("/robots.txt", include_in_schema=False)
async def serve_robots():
    return FileResponse(str(frontend_path / "robots.txt"), headers={"Cache-Control": "public, max-age=86400"})

@app.get("/sitemap.xml", include_in_schema=False)
async def serve_sitemap():
    return FileResponse(str(frontend_path / "sitemap.xml"), headers={"Cache-Control": "public, max-age=86400"})

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

@app.get("/admin/site-registry.js", include_in_schema=False)
async def serve_admin_site_registry():
    """The Master's Eye View's registry — dashboard.html loads this via a
    relative <script src>, which resolves against /admin/, so it needs its
    own route the same way dashboard.html itself does."""
    return FileResponse(
        str(frontend_path / "admin" / "site-registry.js"),
        media_type="application/javascript",
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

@app.get("/sales", include_in_schema=False)
async def serve_sales_login():
    return FileResponse(
        str(frontend_path / "sales" / "login.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.get("/sales/register", include_in_schema=False)
async def serve_sales_register():
    return FileResponse(
        str(frontend_path / "sales" / "register.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.get("/sales/dashboard", include_in_schema=False)
async def serve_sales_dashboard():
    return FileResponse(
        str(frontend_path / "sales" / "dashboard.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.get("/sales/checkout", include_in_schema=False)
async def serve_sales_checkout():
    return FileResponse(
        str(frontend_path / "sales" / "checkout.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.get("/sales/cancel", include_in_schema=False)
async def serve_sales_cancel():
    return FileResponse(
        str(frontend_path / "sales" / "cancel.html"),
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
            "ip_address": get_real_client_ip(request),
            "user_agent": request.headers.get("user-agent", "unknown"),
            "referrer": request.headers.get("referer", ""),
            "created_at": datetime.now(timezone.utc),
        })
        return RedirectResponse(url=f"/?ref={normalized}&price=5000")
    return RedirectResponse(url="/")

# ── Health Check & Public Stats ────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


_sales_count_cache = {"count": 0, "expires_at": 0.0}


@app.get("/api/public/sales-count")
async def get_public_sales_count(db=Depends(get_db)):
    """
    Returns the real, live count of completed sales in database with 30s TTL caching.
    Fallback policy: neutral cached value if database connectivity drops.
    """
    import time
    now = time.time()
    if now < _sales_count_cache["expires_at"]:
        return {"sales_count": _sales_count_cache["count"]}

    if db is None:
        return {"sales_count": _sales_count_cache["count"]}

    try:
        count = await db.payments.count_documents({"status": "success"})
        _sales_count_cache["count"] = count
        _sales_count_cache["expires_at"] = now + 30.0
        return {"sales_count": count}
    except Exception:
        return {"sales_count": _sales_count_cache["count"]}


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
def check_admin_password_rotated(settings):
    """Raises in production if ADMIN_PASSWORD is still the shipped default
    (anyone who reads the public source would have full admin access);
    just warns loudly outside production."""
    if settings.ADMIN_PASSWORD != DEFAULT_ADMIN_PASSWORD:
        return
    warning = (
        "🚨 ADMIN_PASSWORD is still the shipped default — anyone who reads "
        "the public source has full admin access. Set a strong, unique "
        "ADMIN_PASSWORD immediately."
    )
    if settings.APP_ENV == "production":
        raise RuntimeError(warning)
    print(warning)


def check_cors_configured_for_production(settings):
    """Warns (never hard-fails — misconfigured CORS is disruptive, not a
    leaked-credential-grade emergency) if running in production with only
    localhost origins allowed, which would silently break every browser
    request from the real deployed frontend."""
    if settings.APP_ENV != "production":
        return
    origins = settings.cors_origins_list
    if origins and all("localhost" in o or "127.0.0.1" in o for o in origins):
        print(
            "🚨 CORS_ORIGINS is running in production with only localhost/127.0.0.1 "
            f"origins allowed ({origins}) — set it to the real production domain(s) "
            "or every browser request from the live site will be blocked."
        )


def check_app_url_configured_for_production(settings):
    """Hard-fails startup in production if APP_URL is pointing to localhost or 127.0.0.1
    or is empty — every emailed access link and sequence link depends on APP_URL."""
    if settings.APP_ENV != "production":
        return
    url = (settings.APP_URL or "").strip().lower()
    if not url or "localhost" in url or "127.0.0.1" in url:
        raise RuntimeError(
            f"CRITICAL CONFIGURATION ERROR: APP_ENV is set to 'production', but APP_URL "
            f"('{settings.APP_URL}') points to localhost/127.0.0.1 or is empty! All customer "
            "library access links and sequence email links would silently break."
        )


@app.on_event("startup")
async def startup():
    check_admin_password_rotated(settings)
    check_cors_configured_for_production(settings)
    check_app_url_configured_for_production(settings)
    await connect_db()
    if settings.RUN_SCHEDULERS:
        start_scheduler()
        start_payout_scheduler()
        start_nudge_scheduler()
        start_subscription_scheduler()
        start_alert_scheduler()
        print("⏰ Background schedulers started")
    else:
        print("⏸️ Background schedulers disabled (RUN_SCHEDULERS=false)")
    print(f"🚀 {settings.APP_NAME} API started")

@app.on_event("shutdown")
async def shutdown():
    if settings.RUN_SCHEDULERS:
        stop_scheduler()
        stop_payout_scheduler()
        stop_nudge_scheduler()
        stop_subscription_scheduler()
        stop_alert_scheduler()
    await disconnect_db()
