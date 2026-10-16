from app.matching import normalize

from .conftest import ADMIN, HOOK, send_tx


def summary(client, user):
    return client.get("/me/summary", headers=user["auth"]).json()


def ledger_balanced(client):
    assert client.get("/admin/ledger/health", headers=ADMIN).json()["balanced"] is True


def test_normalize_descriptor():
    assert normalize("COMPRA TARJ. 1234 Frutería La Huerta S.L. ZARAGOZA ES") == "FRUTERIA LA HUERTA ZARAGOZA"


def test_purchase_generates_pending_reward(client, merchant, user):
    r = send_tx(client, "tx1", 4000).json()
    assert r["status"] == "REWARDED"
    assert r["reward_cents"] == 200  # 5 % de 40 €
    s = summary(client, user)
    assert s["pending_cents"] == 200 and s["total_cents"] == 200
    ledger_balanced(client)


def test_webhook_is_idempotent(client, merchant, user):
    send_tx(client, "tx1", 4000)
    again = send_tx(client, "tx1", 4000).json()
    assert again["duplicate"] is True
    assert summary(client, user)["pending_cents"] == 200


def test_unmatched_and_unknown_card(client, merchant, user):
    assert send_tx(client, "tx1", 4000, descriptor="GASOLINERA X").json()["status"] == "UNMATCHED"
    assert send_tx(client, "tx2", 4000, card_token="tok_otro").json()["status"] == "IGNORED_UNKNOWN_CARD"
    assert summary(client, user)["total_cents"] == 0


def test_webhook_requires_secret(client):
    r = client.post("/webhooks/transactions", json={}, headers={"X-Webhook-Secret": "mal"})
    assert r.status_code == 401


def test_refunds_reverse_pending_reward(client, merchant, user):
    send_tx(client, "tx1", 4000)
    partial = send_tx(client, "rf1", -1000, booked_at="2026-01-12T10:00:00").json()
    assert partial["status"] == "REFUND_APPLIED"
    assert summary(client, user)["pending_cents"] == 150
    send_tx(client, "rf2", -3000, booked_at="2026-01-13T10:00:00")
    assert summary(client, user)["pending_cents"] == 0
    rewards = client.get("/me/rewards", headers=user["auth"]).json()
    assert rewards[0]["status"] == "REVERSED"
    ledger_balanced(client)


def test_full_lifecycle_until_payout(client, merchant, user):
    send_tx(client, "tx1", 4000)   # 200 usuario + 60 plataforma
    send_tx(client, "tx2", 10000)  # 500 usuario + 150 plataforma

    # Antes de 30 días no se confirma nada
    assert client.post("/admin/jobs/confirm-rewards?now=2026-01-20T00:00:00", headers=ADMIN).json()["confirmed"] == 0
    assert client.post("/admin/jobs/confirm-rewards?now=2026-02-15T00:00:00", headers=ADMIN).json()["confirmed"] == 2
    assert summary(client, user)["confirmed_cents"] == 700

    # Sin cobro al comercio no se envía nada a la gestora
    assert client.post("/admin/payouts", headers=ADMIN).json() is None

    st = client.get(f"/admin/merchants/{merchant['id']}/statement", headers=ADMIN).json()
    assert st["amount_due_cents"] == 910
    paid = client.post(
        f"/admin/merchants/{merchant['id']}/payments",
        json={"amount_cents": 910, "reference": "SEPA-001"},
        headers=ADMIN,
    ).json()
    assert paid["rewards_covered"] == 2

    batch = client.post("/admin/payouts", headers=ADMIN).json()
    assert batch["total_cents"] == 700
    csv_text = client.get(f"/admin/payouts/{batch['id']}/file", headers=ADMIN).text
    assert "700" in csv_text.splitlines()[1]

    s = summary(client, user)
    assert (s["pending_cents"], s["confirmed_cents"], s["invested_cents"]) == (0, 0, 700)
    ledger_balanced(client)


def test_partial_merchant_payment_covers_fifo(client, merchant, user):
    send_tx(client, "tx1", 4000)   # coste 260
    send_tx(client, "tx2", 10000)  # coste 650
    client.post("/admin/jobs/confirm-rewards?now=2026-03-01T00:00:00", headers=ADMIN)
    r = client.post(
        f"/admin/merchants/{merchant['id']}/payments",
        json={"amount_cents": 500, "reference": "SEPA-A"},
        headers=ADMIN,
    ).json()
    assert r["rewards_covered"] == 1
    assert client.post("/admin/payouts", headers=ADMIN).json()["total_cents"] == 200
    # El resto del pago (240) + nuevo pago (410) cubre la segunda
    r = client.post(
        f"/admin/merchants/{merchant['id']}/payments",
        json={"amount_cents": 410, "reference": "SEPA-B"},
        headers=ADMIN,
    ).json()
    assert r["rewards_covered"] == 1
    ledger_balanced(client)


def test_offer_cap_and_minimum(client, user):
    m = client.post("/admin/merchants", json={"name": "Óptica", "cif": "B2"}, headers=ADMIN).json()
    client.post(f"/admin/merchants/{m['id']}/locations", json={"descriptor_pattern": "OPTICA VISION"}, headers=ADMIN)
    client.post(
        f"/admin/merchants/{m['id']}/offers",
        json={"user_bps": 1000, "platform_bps": 100, "min_amount_cents": 2000, "max_user_reward_cents": 1500,
              "valid_from": "2020-01-01T00:00:00"},
        headers=ADMIN,
    )
    assert send_tx(client, "o1", 1500, descriptor="OPTICA VISION", mcc=None).json()["status"] == "NO_OFFER"
    assert send_tx(client, "o2", 50000, descriptor="OPTICA VISION", mcc=None).json()["reward_cents"] == 1500


def test_public_merchant_list_and_projection(client, merchant, user):
    merchants = client.get("/merchants").json()
    assert merchants[0]["user_pct"] == 5.0
    send_tx(client, "tx1", 4000)
    p = client.get("/me/projection?monthly_cents=1000&years=10&annual_return_pct=0", headers=user["auth"]).json()
    assert p["projected_cents"] == 200 + 1000 * 120


def test_auth(client):
    client.post("/auth/register", json={"email": "b@example.com", "name": "B", "password": "secreto123"})
    assert client.post("/auth/login", json={"email": "b@example.com", "password": "mal12345"}).status_code == 401
    assert client.post("/auth/login", json={"email": "b@example.com", "password": "secreto123"}).status_code == 200
    assert client.get("/me").status_code == 401
    assert client.post("/admin/payouts").status_code == 403


def test_confirm_then_statement_in_same_session(client, merchant, user):
    """Confirmar y facturar en la misma sesión (como hace un job) debe ver los cambios sin commit."""
    from app.db import SessionLocal
    from app.models import utcnow
    from app.rewards import confirm_due_rewards, merchant_amount_due

    send_tx(client, "tx1", 4000)
    db = SessionLocal()
    assert confirm_due_rewards(db, utcnow()) == 1
    assert merchant_amount_due(db, merchant["id"])[0] == 260
    db.rollback()
