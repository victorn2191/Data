import os
import tempfile

# Base de datos aislada para los tests (antes de importar la app)
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["HOLD_DAYS"] = "30"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

ADMIN = {"X-Admin-Key": "dev-admin-key"}
HOOK = {"X-Webhook-Secret": "dev-webhook-secret"}


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def merchant(client):
    """Comercio con oferta: 5 % para el usuario y 1,5 % para la plataforma."""
    m = client.post("/admin/merchants", json={"name": "Frutería La Huerta", "cif": "B1"}, headers=ADMIN).json()
    client.post(
        f"/admin/merchants/{m['id']}/locations",
        json={"descriptor_pattern": "FRUTERIA LA HUERTA", "mcc": "5411"},
        headers=ADMIN,
    )
    client.post(
        f"/admin/merchants/{m['id']}/offers",
        json={"user_bps": 500, "platform_bps": 150, "valid_from": "2020-01-01T00:00:00"},
        headers=ADMIN,
    )
    return m


@pytest.fixture()
def user(client):
    """Usuario registrado, con cuenta en la gestora y tarjeta vinculada."""
    r = client.post("/auth/register", json={"email": "ana@example.com", "name": "Ana", "password": "secreto123"})
    auth = {"Authorization": f"Bearer {r.json()['token']}"}
    client.post("/me/pension-account", headers=auth)
    client.post("/me/cards", json={"provider_token": "tok_ana", "last4": "1111"}, headers=auth)
    return {"auth": auth, "id": r.json()["user_id"]}


def send_tx(client, external_id, amount_cents, descriptor="COMPRA TARJ 1111 FRUTERIA LA HUERTA ZARAGOZA",
            booked_at="2026-01-10T10:00:00", card_token="tok_ana", mcc="5411"):
    return client.post(
        "/webhooks/transactions",
        json={
            "provider": "demo-psd2",
            "external_id": external_id,
            "card_token": card_token,
            "amount_cents": amount_cents,
            "booked_at": booked_at,
            "descriptor": descriptor,
            "mcc": mcc,
        },
        headers=HOOK,
    )
