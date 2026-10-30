"""Contabilidad de doble entrada, inmutable.

Cuentas:
  merchant_receivable:{id}   (activo)   lo que nos debe cada comercio
  cash                       (activo)   cuenta bancaria de la plataforma
  user_pending:{id}          (pasivo)   aportaciones pendientes del usuario
  user_confirmed:{id}        (pasivo)   aportaciones firmes aún no enviadas a la gestora
  user_invested:{id}         (memoria)  total enviado a la gestora (solo informativo)
  platform_revenue_pending   (ingreso)  margen pendiente
  platform_revenue           (ingreso)  margen firme

Nunca se modifica un apunte: las correcciones son asientos nuevos.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Journal, LedgerEntry


class UnbalancedJournal(ValueError):
    pass


def post(db: Session, kind: str, reference: str, lines: list[tuple[str, int, int]]) -> Journal:
    """Registra un asiento. `lines` = [(cuenta, debe, haber), ...] en céntimos."""
    lines = [(acc, d, c) for acc, d, c in lines if d or c]
    total_debit = sum(d for _, d, _ in lines)
    total_credit = sum(c for _, _, c in lines)
    if total_debit != total_credit:
        raise UnbalancedJournal(f"{kind} {reference}: debe {total_debit} != haber {total_credit}")
    if any(d < 0 or c < 0 for _, d, c in lines):
        raise ValueError("Los importes de un apunte no pueden ser negativos")
    journal = Journal(kind=kind, reference=reference)
    db.add(journal)
    db.flush()
    for account, debit, credit in lines:
        db.add(LedgerEntry(journal_id=journal.id, account=account, debit_cents=debit, credit_cents=credit))
    db.flush()
    return journal


def balance(db: Session, account: str) -> int:
    """Saldo deudor (debe - haber). Para cuentas de pasivo/ingreso será negativo."""
    stmt = select(
        func.coalesce(func.sum(LedgerEntry.debit_cents), 0) - func.coalesce(func.sum(LedgerEntry.credit_cents), 0)
    ).where(LedgerEntry.account == account)
    return int(db.execute(stmt).scalar_one())


def credit_balance(db: Session, account: str) -> int:
    """Saldo acreedor (haber - debe), útil para cuentas de pasivo e ingresos."""
    return -balance(db, account)


def trial_balance(db: Session) -> int:
    """Suma de todos los saldos. Debe ser siempre 0."""
    stmt = select(
        func.coalesce(func.sum(LedgerEntry.debit_cents), 0) - func.coalesce(func.sum(LedgerEntry.credit_cents), 0)
    )
    return int(db.execute(stmt).scalar_one())
