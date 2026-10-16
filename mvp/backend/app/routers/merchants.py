from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Merchant, MerchantLocation, Offer, utcnow
from ..rewards import find_offer
from ..schemas import LocationIn, LocationOut, MerchantIn, MerchantOut, MerchantPublicOut, OfferIn, OfferOut
from ..security import require_admin

public = APIRouter(prefix="/merchants", tags=["comercios"])
admin = APIRouter(prefix="/admin/merchants", tags=["admin"], dependencies=[Depends(require_admin)])


@public.get("", response_model=list[MerchantPublicOut])
def list_merchants(category: str | None = None, db: Session = Depends(get_db)):
    """Comercios activos con su porcentaje de aportación vigente (para el mapa/listado de la app)."""
    stmt = select(Merchant).where(Merchant.status == "ACTIVE").options(selectinload(Merchant.locations))
    if category:
        stmt = stmt.where(Merchant.category == category)
    now = utcnow()
    result = []
    for m in db.execute(stmt.order_by(Merchant.name)).scalars():
        offer = find_offer(db, m.id, 10**9, now)
        if offer is None:
            continue
        result.append(
            MerchantPublicOut(
                id=m.id,
                name=m.name,
                category=m.category,
                user_pct=offer.user_bps / 100,
                locations=[LocationOut.model_validate(loc) for loc in m.locations],
            )
        )
    return sorted(result, key=lambda x: -x.user_pct)


def _merchant_or_404(db: Session, merchant_id: int) -> Merchant:
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comercio no encontrado")
    return merchant


@admin.post("", response_model=MerchantOut, status_code=status.HTTP_201_CREATED)
def create_merchant(body: MerchantIn, db: Session = Depends(get_db)):
    merchant = Merchant(**body.model_dump())
    db.add(merchant)
    db.commit()
    return merchant


@admin.post("/{merchant_id}/locations", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def add_location(merchant_id: int, body: LocationIn, db: Session = Depends(get_db)):
    _merchant_or_404(db, merchant_id)
    location = MerchantLocation(merchant_id=merchant_id, **body.model_dump())
    db.add(location)
    db.commit()
    return location


@admin.post("/{merchant_id}/offers", response_model=OfferOut, status_code=status.HTTP_201_CREATED)
def add_offer(merchant_id: int, body: OfferIn, db: Session = Depends(get_db)):
    _merchant_or_404(db, merchant_id)
    data = body.model_dump()
    data["valid_from"] = data["valid_from"] or utcnow()
    if data["valid_to"] and data["valid_to"] <= data["valid_from"]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "valid_to debe ser posterior a valid_from")
    offer = Offer(merchant_id=merchant_id, **data)
    db.add(offer)
    db.commit()
    return offer


@admin.delete("/{merchant_id}/offers/{offer_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_offer(merchant_id: int, offer_id: int, db: Session = Depends(get_db)):
    offer = db.get(Offer, offer_id)
    if offer is None or offer.merchant_id != merchant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Oferta no encontrada")
    offer.active = False
    db.commit()
