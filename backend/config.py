"""
Application configuration using pydantic-settings.
All values loaded from environment variables / .env file.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

# Referenced by both the Settings default below and the startup check in
# main.py, so the two can never drift out of sync.
DEFAULT_ADMIN_PASSWORD = "Change-Me-Admin-Password!"


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────
    APP_NAME: str = "Academic Comeback"
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost:8000"
    APP_SECRET_KEY: str = "change-me-to-a-256-bit-random-secret"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:5500"
    RUN_SCHEDULERS: bool = True

    # ── MongoDB ───────────────────────────────────────────────────────
    MONGODB_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "academic_comeback"

    # ── JWT ───────────────────────────────────────────────────────────
    JWT_SECRET: str = "change-me-jwt-secret-very-long-random"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7
    JWT_DOWNLOAD_EXPIRE_MINUTES: int = 10

    # ── Paystack ─────────────────────────────────────────────────────
    PAYSTACK_SECRET_KEY: str = "sk_test_your_paystack_secret_key"
    PAYSTACK_PUBLIC_KEY: str = "pk_test_your_paystack_public_key"
    PRODUCT_PRICE_NAIRA: int = 2000   # Legacy ₦2,000 early-bird
    PRODUCT_PRICE_LATE_NAIRA: int = 5000  # ₦5,000 after 24 hrs
    PRODUCT_PRICE_USD: float = 15.0     # $15 early-bird
    PRODUCT_PRICE_LATE_USD: float = 30.0 # $30 after 24 hrs
    PRODUCT_PRICE_RETAIL_NAIRA: int = 20000  # ₦20,000 standard retail / after 48h affiliate expiry
    PRODUCT_PRICE_RETAIL_USD: float = 100.0  # $100 standard retail / after 48h affiliate expiry
    USD_TO_NGN_RATE: float = 1600.0     # Exchange rate for Paystack NGN fallback (1 USD = 1600 NGN)

    # ── Tiered Pricing Structure ─────────────────────────────────────
    TIER_STARTER_PRICE_NAIRA: int = 3500
    TIER_STARTER_PRICE_USD: float = 22.0
    TIER_COMPLETE_PRICE_NAIRA: int = 6000
    TIER_COMPLETE_PRICE_USD: float = 35.0
    TIER_VIP_PRICE_NAIRA: int = 12500
    TIER_VIP_PRICE_USD: float = 75.0

    # ── Meta Conversions API (server-side Purchase event) ────────────
    # Same Pixel ID already used client-side in index.html/library.html.
    # FB_CAPI_ACCESS_TOKEN is blank by default — meta_capi.py no-ops
    # safely until this is set in Render (Events Manager → this Pixel →
    # Settings → Conversions API → Generate access token).
    FB_PIXEL_ID: str = "1033231049261122"
    FB_CAPI_ACCESS_TOKEN: str = ""

    # ── Meta Conversions API (server-side CompleteRegistration event) ──
    # Separate pixel from the main funnel above — the one added to
    # affiliate-register.html's <head>. Same no-ops-if-blank pattern:
    # FB_AFFILIATE_CAPI_ACCESS_TOKEN comes from Events Manager → this
    # Pixel → Settings → Conversions API → Generate access token.
    FB_AFFILIATE_PIXEL_ID: str = "1075823608450969"
    FB_AFFILIATE_CAPI_ACCESS_TOKEN: str = ""

    # ── SMTP ──────────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = "your@gmail.com"
    SMTP_PASS: str = "your-app-password"
    FROM_EMAIL: str = "Itoya David <your@gmail.com>"

    # ── Admin ─────────────────────────────────────────────────────────
    ADMIN_EMAIL: str = "admin@scalegroup.com"
    ADMIN_PASSWORD: str = DEFAULT_ADMIN_PASSWORD

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
    AFFILIATE_DEFAULT_COMMISSION_PERCENT: float = 60.0
    AFFILIATE_VIDEO_MATERIALS_LINK: str = "https://drive.google.com/drive/folders/1vBqbAgBzUdgEZTcJmJMDLN0MHOd26LfM?usp=sharing"
    WHATSAPP_AFFILIATE_LINK: str = "https://chat.whatsapp.com/GT4EVPIhwQa4DJsXZRbxql?s=cl&p=i&ilr=4"

    # ── Settlement (your own payout destination) ─────────────────────
    # Used only by the periodic "withdraw my share" transfer, once the
    # Flutterwave account is switched to manual settlement (funds
    # accumulate in the payout balance instead of auto-hitting your
    # personal bank). Never exposed in any dashboard response.
    SETTLEMENT_BANK_CODE: str = ""
    SETTLEMENT_ACCOUNT_NUMBER: str = ""
    SETTLEMENT_ACCOUNT_NAME: str = ""

    # ── Abandoned Transaction Recovery (Aggressive Multi-Touch Engine) ───
    ABANDONED_RECOVERY_ENABLED: bool = True
    ABANDONED_RECOVERY_INTERVAL_MINS: int = 5   # Worker check frequency (every 5 minutes)
    ABANDONED_TOUCH_1_MINS: int = 15            # Step 1: 15m (Payment snag + 2-Hour Audio Cram Bonus)
    ABANDONED_TOUCH_2_MINS: int = 120           # Step 2: 2h (Bonus 1 expiring alert)
    ABANDONED_TOUCH_3_MINS: int = 360           # Step 3: 6h (Empathy + Comeback Case Study)
    ABANDONED_TOUCH_4_MINS: int = 720           # Step 4: 12h (Bedtime anxiety check)
    ABANDONED_TOUCH_5_MINS: int = 1080          # Step 5: 18h (Day 2 AM: Exam Survival Template bonus)
    ABANDONED_TOUCH_6_MINS: int = 1440          # Step 6: 24h (Day 2 PM: Social proof & carryover math)
    ABANDONED_TOUCH_7_MINS: int = 1800          # Step 7: 30h (Day 2 Night: Day 2 bonus final call)
    ABANDONED_TOUCH_8_MINS: int = 2520          # Step 8: 42h (Day 3 AM: Cart reservation release)
    ABANDONED_TOUCH_9_MINS: int = 3240          # Step 9: 54h (Day 3 Night: VIP WhatsApp pass + midnight)
    ABANDONED_DAILY_INTERVAL_MINS: int = 1440   # Step 10+: Daily ongoing reminder until purchase
    
    # Backwards compatibility legacy aliases
    ABANDONED_DELAY_MINUTES_1: int = 15
    ABANDONED_DELAY_MINUTES_2: int = 120
    ABANDONED_DELAY_MINUTES_3: int = 360
    ABANDONED_DELAY_MINUTES_4: int = 720
    ABANDONED_DISCOUNT_ENABLED: bool = False
    ABANDONED_DISCOUNT_PERCENT: float = 10.0
    ABANDONED_DISCOUNT_CODE: str = "COMEBACK10"
    ABANDONED_STEP4_PRICE_NAIRA: float = 2000.0
    ABANDONED_STEP4_PRICE_USD: float = 15.0



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
    
    # Allow explicit APP_URL in environment (e.g. custom domain https://academiccomeback.com)
    # to take priority over Render's default RENDER_EXTERNAL_URL (https://academic-pack.onrender.com)
    import os
    env_app_url = os.environ.get("APP_URL", "").strip()
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "").strip()

    if env_app_url and "localhost" not in env_app_url and "127.0.0.1" not in env_app_url:
        s.APP_URL = env_app_url.rstrip("/")
    elif render_url:
        s.APP_URL = render_url.rstrip("/")

    for name, value in list(s.__dict__.items()):
        if isinstance(value, str):
            setattr(s, name, value.strip())
    return s

