"""
Application configuration using pydantic-settings.
All values loaded from environment variables / .env file.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────
    APP_NAME: str = "Academic Comeback"
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost:8000"
    APP_SECRET_KEY: str = "change-me-to-a-256-bit-random-secret"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:5500"

    # ── MongoDB ───────────────────────────────────────────────────────
    MONGODB_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "academic_comeback"

    # ── JWT ───────────────────────────────────────────────────────────
    JWT_SECRET: str = "change-me-jwt-secret-very-long-random"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7
    JWT_DOWNLOAD_EXPIRE_MINUTES: int = 10

    # ── Flutterwave V4 (replaces Paystack) ───────────────────────────
    FLW_CLIENT_ID: str = "your-flutterwave-client-id"
    FLW_CLIENT_SECRET: str = "your-flutterwave-client-secret"
    FLW_WEBHOOK_SECRET_HASH: str = ""  # Set in Flutterwave Dashboard → Settings → Webhooks
    FLW_VIRTUAL_ACCOUNT_BANK_CODE: str = "035"  # Wema Bank — issuing bank for dynamic virtual accounts
    PRODUCT_PRICE_NAIRA: int = 2000   # ₦2,000 early-bird
    PRODUCT_PRICE_LATE_NAIRA: int = 5000  # ₦5,000 after 24 hrs

    # ── Meta Conversions API (server-side Purchase event) ────────────
    # Same Pixel ID already used client-side in index.html/welcome.html.
    # FB_CAPI_ACCESS_TOKEN is blank by default — meta_capi.py no-ops
    # safely until this is set in Render (Events Manager → this Pixel →
    # Settings → Conversions API → Generate access token).
    FB_PIXEL_ID: str = "1033231049261122"
    FB_CAPI_ACCESS_TOKEN: str = ""

    # ── SMTP ──────────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "your@gmail.com"
    SMTP_PASS: str = "your-app-password"
    FROM_EMAIL: str = "Itoya David <your@gmail.com>"

    # ── Admin ─────────────────────────────────────────────────────────
    ADMIN_EMAIL: str = "admin@scalegroup.com"
    ADMIN_PASSWORD: str = "Change-Me-Admin-Password!"

    # ── WhatsApp ──────────────────────────────────────────────────────
    WHATSAPP_CHANNEL_LINK: str = "https://chat.whatsapp.com/your-channel-link"
    WHATSAPP_COMMUNITY_LINK: str = "https://chat.whatsapp.com/Ia7VkMigSlq2NIRQt7A3yj"

    # ── File Storage ──────────────────────────────────────────────────
    UPLOADS_DIR: str = "uploads/products"
    MAX_FILE_SIZE_MB: int = 50

    # ── Affiliates ────────────────────────────────────────────────────
    # Each affiliate's real rate lives on their own document (admin-
    # editable per affiliate) — this is only the starting value applied
    # when a new affiliate is created with no explicit rate given.
    AFFILIATE_DEFAULT_COMMISSION_PERCENT: float = 20.0

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    s = Settings()
    for name, value in list(s.__dict__.items()):
        if isinstance(value, str):
            setattr(s, name, value.strip())
    return s
