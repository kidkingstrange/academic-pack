"""
Pydantic v2 schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ─── Lead ────────────────────────────────────────────────────────────────────
class LeadCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr


class LeadResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime


# ─── Payment ──────────────────────────────────────────────────────────────────
class PaymentInitRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    client_expiry: Optional[float] = None  # ms timestamp from frontend
    payment_method: Optional[str] = "pay_with_bank"  # "pay_with_bank" | "bank_transfer"


class PaymentInitResponse(BaseModel):
    """
    Flutterwave bank-transfer response — shows virtual account to customer.
    """
    reference: str
    charge_id: Optional[str] = None
    va_id: Optional[str] = None
    action: str = "bank_transfer"       # "redirect" | "bank_transfer" | "virtual_account"
    redirect_url: Optional[str] = None  # used when action == "redirect"
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    amount: int
    amount_with_fee: Optional[int] = None  # amount customer actually transfers (includes 2% fee)
    expiry: Optional[str] = None  # ISO datetime when virtual account expires
    note: Optional[str] = None


class PaymentVerifyRequest(BaseModel):
    charge_id: Optional[str] = None
    va_id: Optional[str] = None
    reference: str
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    payment_method: Optional[str] = "pay_with_bank"


class PaymentVerifyResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    magic_link: Optional[str] = None
    message: Optional[str] = None
    amount: Optional[float] = None


# ─── Auth ─────────────────────────────────────────────────────────────────────
class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Library / Products ──────────────────────────────────────────────────────
class ProductPublic(BaseModel):
    id: str
    title: str
    description: str
    thumbnail: Optional[str] = None
    order: int


class LibraryResponse(BaseModel):
    products: List[ProductPublic]
    user_name: str


# ─── Download ─────────────────────────────────────────────────────────────────
class DownloadSignResponse(BaseModel):
    signed_url: str
    expires_in: int  # seconds


# ─── Subscriber ───────────────────────────────────────────────────────────────
class SubscriberCreate(BaseModel):
    name: str
    email: EmailStr


# ─── Admin Analytics ──────────────────────────────────────────────────────────
class AnalyticsSummary(BaseModel):
    total_sales: int
    total_revenue: float
    total_leads: int
    conversion_rate: float
    total_subscribers: int
    pending_emails: int
    downloads_today: int


# ─── Post-purchase survey ─────────────────────────────────────────────────────
class SurveyResponseRequest(BaseModel):
    token: str  # library_access_token — same identification as /api/library
    answers: dict = {}
