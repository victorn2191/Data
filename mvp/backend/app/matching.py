"""Identificación del comercio a partir del descriptor bancario.

Los descriptores son ruidosos ("COMPRA TARJ. 1234 MERCADONA S.A. ZARAGOZA ES"),
así que se normalizan y se busca el patrón más largo que aparezca en el texto.
"""

import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Merchant, MerchantLocation

_NOISE = re.compile(r"\b(COMPRA|TARJ|TARJETA|PAGO|CON|EN|POS|TPV|SA|SL|SAU|ES|ESP)\b")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.upper().replace(".", "")  # "S.L." -> "SL"
    text = re.sub(r"[^A-Z ]+", " ", text)
    text = _NOISE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class MatchResult:
    merchant_id: int
    location_id: int
    confidence: float


def match_merchant(db: Session, descriptor: str, mcc: str | None) -> MatchResult | None:
    norm = f" {normalize(descriptor)} "
    stmt = (
        select(MerchantLocation)
        .join(Merchant)
        .where(Merchant.status == "ACTIVE")
    )
    best: tuple[int, MatchResult] | None = None
    for loc in db.execute(stmt).scalars():
        pattern = normalize(loc.descriptor_pattern)
        if not pattern or f" {pattern} " not in norm:
            continue
        if loc.mcc and mcc and loc.mcc != mcc:
            continue
        confidence = 1.0 if (loc.mcc and mcc == loc.mcc) else 0.8
        score = len(pattern) * 10 + int(confidence * 10)
        if best is None or score > best[0]:
            best = (score, MatchResult(loc.merchant_id, loc.id, confidence))
    return best[1] if best else None
