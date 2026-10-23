"""Carga datos de demostración: comercios, ofertas, un usuario con tarjeta y compras.

Uso:  python -m app.seed
Usuario demo: demo@futuroya.com / demo12345
"""

import random
from datetime import timedelta

from sqlalchemy import select

from .db import SessionLocal, init_db
from .models import LinkedCard, Merchant, MerchantLocation, Offer, PensionAccount, Transaction, User, utcnow
from .rewards import confirm_due_rewards, create_payout_batch, merchant_amount_due, process_transaction, record_merchant_payment
from .security import hash_password

MERCHANTS = [
    # nombre, cif, categoría, patrón descriptor, mcc, % usuario (pb), % plataforma (pb), dirección, lat, lng
    ("Frutería La Huerta", "B50000001", "alimentación", "FRUTERIA LA HUERTA", "5411", 500, 150, "C/ Alfonso I 12, Zaragoza", 41.6535, -0.8796),
    ("Librería Cervantes", "B50000002", "cultura", "LIBRERIA CERVANTES", "5942", 400, 100, "C/ Don Jaime 5, Zaragoza", 41.6529, -0.8768),
    ("Óptica Visión", "B50000003", "salud", "OPTICA VISION", "8043", 600, 200, "Pº Independencia 20, Zaragoza", 41.6487, -0.8837),
    ("Café del Mercado", "B50000004", "restauración", "CAFE DEL MERCADO", "5814", 300, 100, "Pl. Lanuza 1, Zaragoza", 41.6540, -0.8810),
    ("Deportes Moncayo", "B50000005", "deporte", "DEPORTES MONCAYO", "5941", 350, 100, "C/ Delicias 40, Zaragoza", 41.6460, -0.9010),
    ("Supermercado Ebro", "B50000006", "alimentación", "SUPER EBRO", "5411", 150, 50, "Av. Goya 30, Zaragoza", 41.6450, -0.8890),
]


def run() -> None:
    init_db()
    db = SessionLocal()
    if db.execute(select(User).where(User.email == "demo@futuroya.com")).scalar_one_or_none():
        print("Los datos de demo ya existen.")
        return

    merchants = []
    for name, cif, cat, pattern, mcc, ubps, pbps, addr, lat, lng in MERCHANTS:
        m = Merchant(name=name, cif=cif, category=cat, sepa_mandate_id=f"MNDT-{cif}")
        db.add(m)
        db.flush()
        db.add(MerchantLocation(merchant_id=m.id, descriptor_pattern=pattern, mcc=mcc, address=addr, lat=lat, lng=lng))
        db.add(Offer(merchant_id=m.id, user_bps=ubps, platform_bps=pbps, valid_from=utcnow() - timedelta(days=365)))
        merchants.append((m, pattern, mcc))

    user = User(email="demo@futuroya.com", name="Lucía Demo", password_hash=hash_password("demo12345"), kyc_status="VERIFIED")
    db.add(user)
    db.flush()
    db.add(PensionAccount(user_id=user.id, provider="demo-gestora", external_account_id="PP-DEMO0001"))
    card = LinkedCard(user_id=user.id, provider="demo-psd2", provider_token="tok_demo_visa", last4="4242")
    db.add(card)
    db.flush()

    rng = random.Random(42)
    now = utcnow()
    for i in range(40):
        m, pattern, mcc = rng.choice(merchants)
        booked = now - timedelta(days=rng.randint(0, 120), hours=rng.randint(0, 23))
        tx = Transaction(
            provider="demo-psd2",
            external_id=f"seed-{i}",
            user_id=user.id,
            card_id=card.id,
            amount_cents=rng.randint(800, 9000),
            booked_at=booked,
            raw_descriptor=f"COMPRA TARJ. 4242 {pattern} ZARAGOZA ES",
            mcc=mcc,
        )
        db.add(tx)
        db.flush()
        process_transaction(db, tx)
    # Una compra fuera de la red (no genera aportación)
    db.add(Transaction(provider="demo-psd2", external_id="seed-x", user_id=user.id, card_id=card.id,
                       amount_cents=2500, booked_at=now, raw_descriptor="GASOLINERA CUALQUIERA", status="UNMATCHED"))

    confirm_due_rewards(db, now)
    # Los comercios pagan lo confirmado y se envía un lote a la gestora
    for m, *_ in merchants:
        due, _ = merchant_amount_due(db, m.id)
        if due:
            record_merchant_payment(db, m.id, due, f"SEPA-{m.cif}-seed")
    create_payout_batch(db)
    db.commit()
    print("Datos de demo cargados. Usuario: demo@futuroya.com / demo12345")


if __name__ == "__main__":
    run()
