from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import LinkedCard, Reward, Transaction, TxStatus
from ..rewards import process_transaction
from ..schemas import TransactionResultOut, TransactionWebhookIn
from ..security import require_webhook_secret

router = APIRouter(prefix="/webhooks", tags=["webhooks"], dependencies=[Depends(require_webhook_secret)])


def _result(db: Session, tx: Transaction, duplicate: bool) -> TransactionResultOut:
    reward = db.execute(select(Reward).where(Reward.transaction_id == tx.id)).scalar_one_or_none()
    return TransactionResultOut(
        transaction_id=tx.id,
        status=tx.status,
        duplicate=duplicate,
        merchant_id=tx.matched_merchant_id,
        reward_cents=reward.user_amount_cents if reward else None,
    )


@router.post("/transactions", response_model=TransactionResultOut)
def ingest_transaction(body: TransactionWebhookIn, db: Session = Depends(get_db)):
    """Recibe una operación de tarjeta del agregador PSD2 / proveedor CLO.

    Idempotente por (provider, external_id): los reintentos del proveedor no duplican aportaciones.
    """
    existing = db.execute(
        select(Transaction).where(Transaction.provider == body.provider, Transaction.external_id == body.external_id)
    ).scalar_one_or_none()
    if existing:
        return _result(db, existing, duplicate=True)

    card = db.execute(
        select(LinkedCard).where(LinkedCard.provider_token == body.card_token, LinkedCard.status == "ACTIVE")
    ).scalar_one_or_none()
    if card is None:
        # Tarjeta desconocida o revocada: no guardamos datos de quien no ha dado su consentimiento
        return TransactionResultOut(transaction_id=0, status="IGNORED_UNKNOWN_CARD")

    tx = Transaction(
        provider=body.provider,
        external_id=body.external_id,
        user_id=card.user_id,
        card_id=card.id,
        amount_cents=body.amount_cents,
        currency=body.currency,
        booked_at=body.booked_at.replace(tzinfo=None),
        raw_descriptor=body.descriptor,
        mcc=body.mcc,
    )
    if body.currency != "EUR":
        tx.status = TxStatus.NEEDS_REVIEW
        db.add(tx)
        db.commit()
        return _result(db, tx, duplicate=False)
    try:
        db.add(tx)
        db.flush()
        process_transaction(db, tx)
        db.commit()
    except IntegrityError:
        # Carrera entre dos entregas del mismo evento
        db.rollback()
        existing = db.execute(
            select(Transaction).where(
                Transaction.provider == body.provider, Transaction.external_id == body.external_id
            )
        ).scalar_one()
        return _result(db, existing, duplicate=True)
    return _result(db, tx, duplicate=False)
