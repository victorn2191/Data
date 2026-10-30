from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import ledger
from ..db import get_db
from ..models import Merchant, PayoutBatch, Transaction, TxStatus
from ..rewards import confirm_due_rewards, create_payout_batch, merchant_amount_due, record_merchant_payment
from ..schemas import MerchantPaymentIn, PayoutOut
from ..security import require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/jobs/confirm-rewards")
def run_confirm(now: datetime | None = None, db: Session = Depends(get_db)):
    """Job diario: confirma aportaciones fuera de la ventana de devolución."""
    count = confirm_due_rewards(db, now.replace(tzinfo=None) if now else None)
    db.commit()
    return {"confirmed": count}


@router.get("/merchants/{merchant_id}/statement")
def merchant_statement(merchant_id: int, db: Session = Depends(get_db)):
    """Importe que hay que cobrar al comercio (base para la factura y el cobro mensual)."""
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comercio no encontrado")
    due, rewards = merchant_amount_due(db, merchant_id)
    return {
        "merchant_id": merchant_id,
        "merchant": merchant.name,
        "amount_due_cents": due,
        "rewards": len(rewards),
        "receivable_balance_cents": ledger.balance(db, f"merchant_receivable:{merchant_id}"),
    }


@router.post("/merchants/{merchant_id}/payments")
def merchant_payment(merchant_id: int, body: MerchantPaymentIn, db: Session = Depends(get_db)):
    if db.get(Merchant, merchant_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comercio no encontrado")
    covered = record_merchant_payment(db, merchant_id, body.amount_cents, body.reference)
    db.commit()
    return {"rewards_covered": covered}


@router.post("/payouts", response_model=PayoutOut | None)
def run_payout(db: Session = Depends(get_db)):
    """Genera el lote de aportaciones para la gestora (mensual)."""
    batch = create_payout_batch(db)
    db.commit()
    return batch


@router.get("/payouts/{batch_id}/file")
def payout_file(batch_id: int, db: Session = Depends(get_db)):
    batch = db.get(PayoutBatch, batch_id)
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lote no encontrado")
    return Response(
        batch.file_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="lote_{batch_id}.csv"'},
    )


@router.get("/review-queue")
def review_queue(db: Session = Depends(get_db)):
    """Transacciones que necesitan revisión manual (devoluciones tardías, divisas...)."""
    rows = db.execute(
        select(Transaction).where(Transaction.status == TxStatus.NEEDS_REVIEW).order_by(Transaction.booked_at)
    ).scalars()
    return [
        {
            "id": t.id,
            "user_id": t.user_id,
            "amount_cents": t.amount_cents,
            "currency": t.currency,
            "descriptor": t.raw_descriptor,
            "booked_at": t.booked_at,
        }
        for t in rows
    ]


@router.get("/ledger/health")
def ledger_health(db: Session = Depends(get_db)):
    total = ledger.trial_balance(db)
    return {"balanced": total == 0, "trial_balance_cents": total}
