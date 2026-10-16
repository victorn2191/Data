from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Usuarios ---
class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    token: str
    user_id: int


class UserOut(ORM):
    id: int
    email: str
    name: str
    kyc_status: str


class PensionAccountOut(ORM):
    id: int
    provider: str
    external_account_id: str
    status: str


class CardIn(BaseModel):
    # En producción el token llega del flujo de consentimiento PSD2 / CLO, no del cliente
    provider: str = "demo-psd2"
    provider_token: str = Field(min_length=4)
    last4: str = Field(pattern=r"^\d{4}$")
    brand: str = "VISA"


class CardOut(ORM):
    id: int
    provider: str
    last4: str
    brand: str
    status: str


class SummaryOut(BaseModel):
    pending_cents: int
    confirmed_cents: int
    invested_cents: int
    total_cents: int
    rewards_count: int


class RewardOut(BaseModel):
    id: int
    merchant: str
    purchase_cents: int
    user_amount_cents: int
    status: str
    booked_at: datetime


class ProjectionOut(BaseModel):
    years: int
    monthly_cents: int
    annual_return_pct: float
    contributed_cents: int
    projected_cents: int


# --- Comercios ---
class MerchantIn(BaseModel):
    name: str
    cif: str
    category: str = "general"
    sepa_mandate_id: str | None = None


class LocationIn(BaseModel):
    descriptor_pattern: str
    mcc: str | None = Field(default=None, pattern=r"^\d{4}$")
    address: str | None = None
    lat: float | None = None
    lng: float | None = None


class OfferIn(BaseModel):
    user_bps: int = Field(ge=0, le=5000)
    platform_bps: int = Field(ge=0, le=5000)
    min_amount_cents: int = 0
    max_user_reward_cents: int | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None


class OfferOut(ORM):
    id: int
    user_bps: int
    platform_bps: int
    min_amount_cents: int
    max_user_reward_cents: int | None
    valid_to: datetime | None


class LocationOut(ORM):
    id: int
    descriptor_pattern: str
    mcc: str | None
    address: str | None
    lat: float | None
    lng: float | None


class MerchantOut(ORM):
    id: int
    name: str
    category: str
    status: str


class MerchantPublicOut(BaseModel):
    id: int
    name: str
    category: str
    user_pct: float
    locations: list[LocationOut]


class MerchantPaymentIn(BaseModel):
    amount_cents: int = Field(gt=0)
    reference: str


# --- Webhook de transacciones (agregador PSD2 / card-linked offers) ---
class TransactionWebhookIn(BaseModel):
    provider: str
    external_id: str
    card_token: str
    amount_cents: int  # negativo = devolución
    currency: str = "EUR"
    booked_at: datetime
    descriptor: str
    mcc: str | None = None


class TransactionResultOut(BaseModel):
    transaction_id: int
    status: str
    duplicate: bool = False
    merchant_id: int | None = None
    reward_cents: int | None = None


class PayoutOut(ORM):
    id: int
    provider: str
    total_cents: int
    status: str
    created_at: datetime
