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
    referral_code: Optional[str] = None  # captured from /r/CODE via localStorage at checkout


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


# ─── Affiliates ───────────────────────────────────────────────────────────────
# Tracking only — no payout automation. commission_percent is set per
# affiliate (not a single global rate) and can be edited by the admin at
# any time; each recorded conversion locks in the rate that applied at
# that moment (see services/payment_completion.py), so a later rate edit
# never retroactively changes what a past sale owes.
class AffiliateCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    code: Optional[str] = Field(None, min_length=3, max_length=20)
    commission_percent: Optional[float] = Field(None, ge=0, le=100)
    bank_name: Optional[str] = Field(None, max_length=100)
    bank_code: Optional[str] = Field(None, max_length=20)
    account_number: Optional[str] = Field(None, max_length=20)
    account_name: Optional[str] = Field(None, max_length=100)


class AffiliateRegisterRequest(BaseModel):
    # The public self-registration form actively collects and verifies bank
    # details at signup (live account-name resolution via Flutterwave,
    # blocks submit on an invalid account number) — required here to match
    # that real, deliberate UX, unlike AffiliateCreateRequest (the
    # admin-created path), where an admin may not have the affiliate's bank
    # details on hand yet and optional stays correct.
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    bank_name: str = Field(..., min_length=2, max_length=100)
    bank_code: Optional[str] = Field(None, max_length=20)
    account_number: str = Field(..., min_length=10, max_length=20)
    account_name: str = Field(..., min_length=2, max_length=100)


class AffiliateBankDetailsUpdateRequest(BaseModel):
    bank_name: str = Field(..., min_length=2, max_length=100)
    bank_code: Optional[str] = Field(None, max_length=20)
    account_number: str = Field(..., min_length=10, max_length=20)
    account_name: str = Field(..., min_length=2, max_length=100)


class AffiliateCommissionUpdateRequest(BaseModel):
    commission_percent: float = Field(..., ge=0, le=100)
