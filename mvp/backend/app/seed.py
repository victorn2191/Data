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
    # nombre, RUC, categoría, patrón descriptor, mcc, % usuario (pb), % plataforma (pb), dirección, lat, lng
    ("Frutería La Cosecha", "J0310000000001", "alimentación", "FRUTERIA LA COSECHA", "5411", 500, 150, "Altamira, Managua", 12.1180, -86.2510),
    ("Librería El Güegüense", "J0310000000002", "cultura", "LIBRERIA EL GUEGUENSE", "5942", 400, 100, "Los Robles, Managua", 12.1240, -86.2620),
    ("Óptica Visión", "J0310000000003", "salud", "OPTICA VISION", "8043", 600, 200, "Carretera a Masaya, Managua", 12.1050, -86.2490),
    ("Café del Mercado", "J0310000000004", "restauración", "CAFE DEL MERCADO", "5814", 300, 100, "Calle La Calzada, Granada", 11.9300, -85.9560),
    ("Deportes Momotombo", "J0310000000005", "deporte", "DEPORTES MOMOTOMBO", "5941", 350, 100, "Centro, León", 12.4350, -86.8790),
    ("Supermercado Xolotlán", "J0310000000006", "alimentación", "SUPER XOLOTLAN", "5411", 150, 50, "Bolonia, Managua", 12.1430, -86.2730),
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
            amount_cents=rng.randint(30000, 330000),  # C$ 300 – C$ 3,300
            booked_at=booked,
            raw_descriptor=f"COMPRA TARJ. 4242 {pattern} MANAGUA NI",
            mcc=mcc,
        )
        db.add(tx)
        db.flush()
        process_transaction(db, tx)
    # Una compra fuera de la red (no genera aportación)
    db.add(Transaction(provider="demo-psd2", external_id="seed-x", user_id=user.id, card_id=card.id,
                       amount_cents=95000, booked_at=now, raw_descriptor="GASOLINERA CUALQUIERA", status="UNMATCHED"))

    confirm_due_rewards(db, now)
    # Los comercios pagan lo confirmado y se envía un lote a la gestora
    for m, *_ in merchants:
        due, _ = merchant_amount_due(db, m.id)
        if due:
            record_merchant_payment(db, m.id, due, f"PAGO-{m.cif}-seed")
    create_payout_batch(db)
    db.commit()
    print("Datos de demo cargados. Usuario: demo@futuroya.com / demo12345")


if __name__ == "__main__":
    run()
