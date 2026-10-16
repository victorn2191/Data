import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import ledger
from ..config import settings
from ..db import get_db
from ..models import LinkedCard, Merchant, PensionAccount, Reward, RewardStatus, Transaction, User
from ..schemas import (
    CardIn,
    CardOut,
    LoginIn,
    PensionAccountOut,
    ProjectionOut,
    RegisterIn,
    RewardOut,
    SummaryOut,
    TokenOut,
    UserOut,
)
from ..security import current_user, hash_password, issue_token, verify_password

router = APIRouter(tags=["usuarios"])


@router.post("/auth/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.execute(select(User).where(User.email == body.email)).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "El email ya está registrado")
    user = User(email=body.email, name=body.name, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    token = issue_token(db, user)
    db.commit()
    return TokenOut(token=token, user_id=user.id)


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas")
    token = issue_token(db, user)
    db.commit()
    return TokenOut(token=token, user_id=user.id)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post("/me/pension-account", response_model=PensionAccountOut, status_code=status.HTTP_201_CREATED)
def open_pension_account(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Simula el alta en el producto de ahorro de la gestora.

    En producción: KYC + firma de documentación + llamada a la API de la gestora.
    """
    existing = db.execute(select(PensionAccount).where(PensionAccount.user_id == user.id)).scalar_one_or_none()
    if existing:
        return existing
    account = PensionAccount(
        user_id=user.id,
        provider=settings.pension_provider,
        external_account_id=f"PP-{secrets.token_hex(5).upper()}",
    )
    db.add(account)
    user.kyc_status = "VERIFIED"
    db.commit()
    return account


@router.post("/me/cards", response_model=CardOut, status_code=status.HTTP_201_CREATED)
def link_card(body: CardIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if db.execute(select(LinkedCard).where(LinkedCard.provider_token == body.provider_token)).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Tarjeta ya vinculada")
    card = LinkedCard(user_id=user.id, **body.model_dump())
    db.add(card)
    db.commit()
    return card


@router.get("/me/cards", response_model=list[CardOut])
def list_cards(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.execute(select(LinkedCard).where(LinkedCard.user_id == user.id)).scalars().all()


@router.delete("/me/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_card(card_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    card = db.get(LinkedCard, card_id)
    if card is None or card.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarjeta no encontrada")
    card.status = "REVOKED"
    db.commit()


@router.get("/me/summary", response_model=SummaryOut)
def summary(user: User = Depends(current_user), db: Session = Depends(get_db)):
    pending = ledger.credit_balance(db, f"user_pending:{user.id}")
    confirmed = ledger.credit_balance(db, f"user_confirmed:{user.id}")
    invested = ledger.credit_balance(db, f"user_invested:{user.id}")
    count = len(
        db.execute(
            select(Reward.id).where(Reward.user_id == user.id, Reward.status != RewardStatus.REVERSED)
        ).all()
    )
    return SummaryOut(
        pending_cents=pending,
        confirmed_cents=confirmed,
        invested_cents=invested,
        total_cents=pending + confirmed + invested,
        rewards_count=count,
    )


@router.get("/me/rewards", response_model=list[RewardOut])
def rewards(
    limit: int = Query(50, le=200),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Reward, Transaction, Merchant)
        .join(Transaction, Reward.transaction_id == Transaction.id)
        .join(Merchant, Reward.merchant_id == Merchant.id)
        .where(Reward.user_id == user.id)
        .order_by(Transaction.booked_at.desc())
        .limit(limit)
    )
    return [
        RewardOut(
            id=r.id,
            merchant=m.name,
            purchase_cents=t.amount_cents,
            user_amount_cents=r.user_amount_cents,
            status=r.status,
            booked_at=t.booked_at,
        )
        for r, t, m in db.execute(stmt).all()
    ]


@router.get("/me/projection", response_model=ProjectionOut)
def projection(
    monthly_cents: int = Query(..., ge=0, description="Aportación mensual estimada"),
    years: int = Query(..., ge=1, le=60),
    annual_return_pct: float = Query(3.0, ge=-10, le=20),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Simulador de jubilación: saldo actual + aportaciones mensuales con interés compuesto."""
    current = summary(user, db).total_cents
    r = (1 + annual_return_pct / 100) ** (1 / 12) - 1
    months = years * 12
    value = float(current)
    for _ in range(months):
        value = value * (1 + r) + monthly_cents
    return ProjectionOut(
        years=years,
        monthly_cents=monthly_cents,
        annual_return_pct=annual_return_pct,
        contributed_cents=current + monthly_cents * months,
        projected_cents=round(value),
    )
