"""Motor de aportaciones: transacción -> aportación -> confirmación -> cobro -> envío a la gestora."""

import csv
import io
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from . import ledger
from .config import settings
from .matching import match_merchant
from .models import (
    MerchantPayment,
    Offer,
    PayoutBatch,
    PensionAccount,
    Reward,
    RewardStatus,
    Transaction,
    TxStatus,
    utcnow,
)


def find_offer(db: Session, merchant_id: int, amount_cents: int, at: datetime) -> Offer | None:
    stmt = (
        select(Offer)
        .where(
            Offer.merchant_id == merchant_id,
            Offer.active.is_(True),
            Offer.valid_from <= at,
            or_(Offer.valid_to.is_(None), Offer.valid_to > at),
            Offer.min_amount_cents <= amount_cents,
        )
        .order_by(Offer.user_bps.desc())
    )
    return db.execute(stmt).scalars().first()


def compute_split(offer: Offer, amount_cents: int) -> tuple[int, int]:
    """Devuelve (parte usuario, parte plataforma) en céntimos, redondeando a la baja."""
    user = amount_cents * offer.user_bps // 10_000
    if offer.max_user_reward_cents is not None:
        user = min(user, offer.max_user_reward_cents)
    platform = amount_cents * offer.platform_bps // 10_000
    return user, platform


def process_transaction(db: Session, tx: Transaction) -> Reward | None:
    match = match_merchant(db, tx.raw_descriptor, tx.mcc)
    if match is None:
        tx.status = TxStatus.UNMATCHED
        return None
    tx.matched_merchant_id = match.merchant_id
    tx.match_confidence = match.confidence

    if tx.amount_cents < 0:
        _apply_refund(db, tx)
        return None

    offer = find_offer(db, match.merchant_id, tx.amount_cents, tx.booked_at)
    if offer is None:
        tx.status = TxStatus.NO_OFFER
        return None
    user_amount, platform_amount = compute_split(offer, tx.amount_cents)
    if user_amount <= 0:
        tx.status = TxStatus.NO_OFFER
        return None

    reward = Reward(
        transaction_id=tx.id,
        user_id=tx.user_id,
        merchant_id=match.merchant_id,
        offer_id=offer.id,
        user_amount_cents=user_amount,
        platform_amount_cents=platform_amount,
    )
    db.add(reward)
    db.flush()
    ledger.post(
        db,
        "reward_created",
        f"reward:{reward.id}",
        [
            (f"merchant_receivable:{match.merchant_id}", user_amount + platform_amount, 0),
            (f"user_pending:{tx.user_id}", 0, user_amount),
            ("platform_revenue_pending", 0, platform_amount),
        ],
    )
    tx.status = TxStatus.REWARDED
    return reward


def _apply_refund(db: Session, refund: Transaction) -> None:
    """Anula (total o parcialmente) la aportación pendiente más reciente del mismo comercio."""
    refund_abs = -refund.amount_cents
    stmt = (
        select(Reward)
        .join(Transaction, Reward.transaction_id == Transaction.id)
        .where(
            Reward.user_id == refund.user_id,
            Reward.merchant_id == refund.matched_merchant_id,
            Reward.status == RewardStatus.PENDING,
            Transaction.booked_at <= refund.booked_at,
        )
        .order_by(Transaction.booked_at.desc())
    )
    reward = next(
        (
            r
            for r in db.execute(stmt).scalars()
            if r.transaction.amount_cents - r.refunded_purchase_cents >= refund_abs
        ),
        None,
    )
    if reward is None:
        # Ya confirmada/enviada o sin compra original: lo revisa una persona
        refund.status = TxStatus.NEEDS_REVIEW
        return

    remaining = reward.transaction.amount_cents - reward.refunded_purchase_cents
    if refund_abs >= remaining:
        user_back, platform_back = reward.user_amount_cents, reward.platform_amount_cents
    else:
        user_back = reward.user_amount_cents * refund_abs // remaining
        platform_back = reward.platform_amount_cents * refund_abs // remaining

    ledger.post(
        db,
        "reward_reversed",
        f"reward:{reward.id}:refund:{refund.id}",
        [
            (f"user_pending:{reward.user_id}", user_back, 0),
            ("platform_revenue_pending", platform_back, 0),
            (f"merchant_receivable:{reward.merchant_id}", 0, user_back + platform_back),
        ],
    )
    reward.user_amount_cents -= user_back
    reward.platform_amount_cents -= platform_back
    reward.refunded_purchase_cents += refund_abs
    if reward.user_amount_cents == 0:
        reward.status = RewardStatus.REVERSED
    refund.status = TxStatus.REFUND_APPLIED


def confirm_due_rewards(db: Session, now: datetime | None = None) -> int:
    """Confirma las aportaciones cuya ventana de devolución ha terminado (job diario)."""
    now = now or utcnow()
    cutoff = now - timedelta(days=settings.hold_days)
    stmt = (
        select(Reward)
        .join(Transaction, Reward.transaction_id == Transaction.id)
        .where(Reward.status == RewardStatus.PENDING, Transaction.booked_at <= cutoff)
    )
    count = 0
    for reward in db.execute(stmt).scalars():
        ledger.post(
            db,
            "reward_confirmed",
            f"reward:{reward.id}",
            [
                (f"user_pending:{reward.user_id}", reward.user_amount_cents, 0),
                (f"user_confirmed:{reward.user_id}", 0, reward.user_amount_cents),
                ("platform_revenue_pending", reward.platform_amount_cents, 0),
                ("platform_revenue", 0, reward.platform_amount_cents),
            ],
        )
        reward.status = RewardStatus.CONFIRMED
        reward.confirmed_at = now
        count += 1
    return count


def merchant_amount_due(db: Session, merchant_id: int) -> tuple[int, list[Reward]]:
    """Importe a cobrar al comercio: aportaciones confirmadas aún no pagadas."""
    stmt = (
        select(Reward)
        .where(
            Reward.merchant_id == merchant_id,
            Reward.status.in_([RewardStatus.CONFIRMED, RewardStatus.INVESTED]),
            Reward.merchant_paid.is_(False),
        )
        .order_by(Reward.confirmed_at, Reward.id)
    )
    rewards = list(db.execute(stmt).scalars())
    return sum(r.user_amount_cents + r.platform_amount_cents for r in rewards), rewards


def record_merchant_payment(db: Session, merchant_id: int, amount_cents: int, reference: str) -> int:
    """Registra un cobro y marca como pagadas las aportaciones que cubre (FIFO).

    Devuelve cuántas aportaciones quedan cubiertas. Un sobrante queda como saldo a favor.
    """
    if amount_cents <= 0:
        raise ValueError("El importe debe ser positivo")
    db.add(MerchantPayment(merchant_id=merchant_id, amount_cents=amount_cents, reference=reference))
    ledger.post(
        db,
        "merchant_payment",
        reference,
        [("cash", amount_cents, 0), (f"merchant_receivable:{merchant_id}", 0, amount_cents)],
    )
    # Saldo disponible = todo lo cobrado menos lo ya aplicado a aportaciones
    paid_total = sum(
        p.amount_cents
        for p in db.execute(select(MerchantPayment).where(MerchantPayment.merchant_id == merchant_id)).scalars()
    )
    applied = sum(
        r.user_amount_cents + r.platform_amount_cents
        for r in db.execute(
            select(Reward).where(Reward.merchant_id == merchant_id, Reward.merchant_paid.is_(True))
        ).scalars()
    )
    available = paid_total - applied
    _, rewards = merchant_amount_due(db, merchant_id)
    covered = 0
    for reward in rewards:
        cost = reward.user_amount_cents + reward.platform_amount_cents
        if cost > available:
            break
        reward.merchant_paid = True
        available -= cost
        covered += 1
    return covered


def create_payout_batch(db: Session) -> PayoutBatch | None:
    """Agrupa por usuario las aportaciones confirmadas y cobradas, y genera el fichero para la gestora."""
    stmt = select(Reward).where(
        Reward.status == RewardStatus.CONFIRMED,
        Reward.merchant_paid.is_(True),
    )
    by_user: dict[int, list[Reward]] = defaultdict(list)
    for reward in db.execute(stmt).scalars():
        by_user[reward.user_id].append(reward)

    accounts = {
        acc.user_id: acc
        for acc in db.execute(
            select(PensionAccount).where(PensionAccount.user_id.in_(by_user), PensionAccount.status == "ACTIVE")
        ).scalars()
    }
    rows = []
    for user_id, rewards in sorted(by_user.items()):
        account = accounts.get(user_id)
        if account is None:
            continue  # sin cuenta en la gestora: se queda pendiente de envío
        rows.append((account, user_id, rewards, sum(r.user_amount_cents for r in rewards)))
    if not rows:
        return None

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["external_account_id", "user_id", "amount_cents", "num_rewards"])
    for account, user_id, rewards, amount in rows:
        writer.writerow([account.external_account_id, user_id, amount, len(rewards)])

    total = sum(amount for *_, amount in rows)
    batch = PayoutBatch(provider=settings.pension_provider, total_cents=total, file_content=out.getvalue())
    db.add(batch)
    db.flush()

    lines: list[tuple[str, int, int]] = []
    for _, user_id, rewards, amount in rows:
        lines.append((f"user_confirmed:{user_id}", amount, 0))
        for reward in rewards:
            reward.status = RewardStatus.INVESTED
            reward.payout_batch_id = batch.id
    lines.append(("cash", 0, total))
    ledger.post(db, "payout_batch", f"batch:{batch.id}", lines)
    # Cuentas de memoria para mostrar el total invertido de cada usuario
    for _, user_id, _, amount in rows:
        ledger.post(
            db,
            "memo_invested",
            f"batch:{batch.id}:user:{user_id}",
            [("memo_invested_contra", amount, 0), (f"user_invested:{user_id}", 0, amount)],
        )
    return batch
