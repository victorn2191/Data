"""Modelo de datos. Todos los importes se guardan en céntimos (enteros)."""

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RewardStatus(StrEnum):
    PENDING = "PENDING"        # dentro de la ventana de devolución
    CONFIRMED = "CONFIRMED"    # firme, lista para enviarse a la gestora
    INVESTED = "INVESTED"      # enviada a la gestora en un lote
    REVERSED = "REVERSED"      # anulada por devolución


class TxStatus(StrEnum):
    UNMATCHED = "UNMATCHED"            # no es de un comercio adherido
    REWARDED = "REWARDED"              # generó aportación
    NO_OFFER = "NO_OFFER"              # comercio adherido sin oferta vigente
    REFUND_APPLIED = "REFUND_APPLIED"  # devolución que anuló una aportación
    NEEDS_REVIEW = "NEEDS_REVIEW"      # requiere revisión manual


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    kyc_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    pension_account: Mapped["PensionAccount | None"] = relationship(back_populates="user", uselist=False)
    cards: Mapped[list["LinkedCard"]] = relationship(back_populates="user")


class AuthToken(Base):
    __tablename__ = "auth_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class PensionAccount(Base):
    """Cuenta del usuario en el producto de ahorro del socio (plan, PIAS, fondo...)."""

    __tablename__ = "pension_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    provider: Mapped[str] = mapped_column(String(50))
    external_account_id: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    user: Mapped[User] = relationship(back_populates="pension_account")


class LinkedCard(Base):
    """Tarjeta vinculada. Solo se guarda el token del proveedor PSD2/CLO, nunca el PAN."""

    __tablename__ = "linked_cards"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50))
    provider_token: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    last4: Mapped[str] = mapped_column(String(4))
    brand: Mapped[str] = mapped_column(String(20), default="VISA")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    consent_expires_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    user: Mapped[User] = relationship(back_populates="cards")


class Merchant(Base):
    __tablename__ = "merchants"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    cif: Mapped[str] = mapped_column(String(20), unique=True)
    category: Mapped[str] = mapped_column(String(50), default="general")
    sepa_mandate_id: Mapped[str | None] = mapped_column(String(80), default=None)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    locations: Mapped[list["MerchantLocation"]] = relationship(back_populates="merchant")
    offers: Mapped[list["Offer"]] = relationship(back_populates="merchant")


class MerchantLocation(Base):
    """Patrón del descriptor bancario con el que identificamos al comercio."""

    __tablename__ = "merchant_locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    descriptor_pattern: Mapped[str] = mapped_column(String(120))  # normalizado
    mcc: Mapped[str | None] = mapped_column(String(4), default=None)
    address: Mapped[str | None] = mapped_column(String(200), default=None)
    lat: Mapped[float | None] = mapped_column(Float, default=None)
    lng: Mapped[float | None] = mapped_column(Float, default=None)

    merchant: Mapped[Merchant] = relationship(back_populates="locations")


class Offer(Base):
    """Oferta del comercio. Porcentajes en puntos básicos (100 pb = 1 %)."""

    __tablename__ = "offers"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    user_bps: Mapped[int] = mapped_column(Integer)       # parte para el usuario
    platform_bps: Mapped[int] = mapped_column(Integer)   # parte para la plataforma
    min_amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    max_user_reward_cents: Mapped[int | None] = mapped_column(Integer, default=None)
    valid_from: Mapped[datetime] = mapped_column(default=utcnow)
    valid_to: Mapped[datetime | None] = mapped_column(default=None)
    active: Mapped[bool] = mapped_column(default=True)

    merchant: Mapped[Merchant] = relationship(back_populates="offers")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("provider", "external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str] = mapped_column(String(120))  # idempotencia
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("linked_cards.id"))
    amount_cents: Mapped[int] = mapped_column(Integer)  # negativo = devolución
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    booked_at: Mapped[datetime]
    raw_descriptor: Mapped[str] = mapped_column(String(200))
    mcc: Mapped[str | None] = mapped_column(String(4), default=None)
    matched_merchant_id: Mapped[int | None] = mapped_column(ForeignKey("merchants.id"), default=None)
    match_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default=TxStatus.UNMATCHED)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Reward(Base):
    __tablename__ = "rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"))
    user_amount_cents: Mapped[int] = mapped_column(Integer)
    platform_amount_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=RewardStatus.PENDING, index=True)
    # Solo se envía a la gestora lo que el comercio ya ha pagado
    merchant_paid: Mapped[bool] = mapped_column(default=False)
    # Importe de la compra ya devuelto (para devoluciones parciales sucesivas)
    refunded_purchase_cents: Mapped[int] = mapped_column(Integer, default=0)
    payout_batch_id: Mapped[int | None] = mapped_column(ForeignKey("payout_batches.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(default=None)

    transaction: Mapped[Transaction] = relationship()
    merchant: Mapped[Merchant] = relationship()


class Journal(Base):
    """Asiento contable. Sus apuntes deben cuadrar (debe == haber)."""

    __tablename__ = "journals"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    reference: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="journal")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    journal_id: Mapped[int] = mapped_column(ForeignKey("journals.id"), index=True)
    account: Mapped[str] = mapped_column(String(80), index=True)
    debit_cents: Mapped[int] = mapped_column(Integer, default=0)
    credit_cents: Mapped[int] = mapped_column(Integer, default=0)

    journal: Mapped[Journal] = relationship(back_populates="entries")


class PayoutBatch(Base):
    """Lote de aportaciones enviado a la gestora."""

    __tablename__ = "payout_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(50))
    total_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="SENT")
    file_content: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class MerchantPayment(Base):
    """Cobro al comercio (p. ej. adeudo SEPA mensual)."""

    __tablename__ = "merchant_payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    reference: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
