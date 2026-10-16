# Hucha Futura – MVP

MVP de una app de ahorro para la jubilación ligada al consumo (modelo inspirado en Pensumo, ver `docs/pensumo-analisis.md`).
Cada compra con tarjeta en un comercio adherido genera una aportación al plan del usuario, que pagará el comercio.

```
mvp/
├── backend/        API FastAPI + SQLAlchemy (SQLite en local, PostgreSQL en producción)
└── app-prototype/  Prototipo de la app móvil (HTML/JS, funciona en modo demo o contra la API)
```

## Arrancar en local

```bash
cd mvp/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed                 # datos de ejemplo
uvicorn app.main:app --reload      # http://localhost:8000
```

- App: http://localhost:8000/app/ (usuario `demo@hucha-futura.es`, contraseña `demo12345`)
- Documentación de la API: http://localhost:8000/docs
- Tests: `pytest`

Variables de entorno: `DATABASE_URL`, `ADMIN_API_KEY`, `WEBHOOK_SECRET`, `HOLD_DAYS` (30 por defecto), `PENSION_PROVIDER`.

## Ciclo de vida de una aportación

```
Compra con tarjeta ──► webhook PSD2/CLO ──► identificación del comercio ──► oferta vigente
      │
      ▼
  PENDING  (ventana de devolución, HOLD_DAYS)   ← una devolución la anula total o parcialmente
      │  job diario  POST /admin/jobs/confirm-rewards
      ▼
  CONFIRMED  ──► se factura al comercio (statement) ──► cobro SEPA  POST /admin/merchants/{id}/payments
      │  solo lo ya cobrado
      ▼
  INVESTED   lote mensual a la gestora  POST /admin/payouts  (+ fichero CSV)
```

Cada paso queda registrado en una **contabilidad de doble entrada** (`app/ledger.py`); `GET /admin/ledger/health` comprueba que cuadra.

## Endpoints principales

| Ámbito | Endpoint |
|---|---|
| Usuario | `POST /auth/register`, `POST /auth/login`, `GET /me`, `POST /me/pension-account`, `POST/GET/DELETE /me/cards`, `GET /me/summary`, `GET /me/rewards`, `GET /me/projection` |
| Público | `GET /merchants` |
| Proveedor de datos | `POST /webhooks/transactions` (cabecera `X-Webhook-Secret`, idempotente) |
| Backoffice | `/admin/merchants` (+ locations, offers), `/admin/jobs/confirm-rewards`, `/admin/merchants/{id}/statement`, `/admin/merchants/{id}/payments`, `/admin/payouts`, `/admin/review-queue`, `/admin/ledger/health` (cabecera `X-Admin-Key`) |

Ejemplo de transacción entrante:

```bash
curl -X POST localhost:8000/webhooks/transactions \
  -H 'X-Webhook-Secret: dev-webhook-secret' -H 'Content-Type: application/json' \
  -d '{"provider":"demo-psd2","external_id":"tx-001","card_token":"tok_demo_visa",
       "amount_cents":4250,"booked_at":"2026-10-16T10:00:00",
       "descriptor":"COMPRA TARJ. 4242 FRUTERIA LA HUERTA ZARAGOZA ES","mcc":"5411"}'
```

## Qué está simulado y qué falta para producción

| Simulado en el MVP | En producción |
|---|---|
| Alta en el plan (`/me/pension-account`) | KYC real + contratación con la gestora/aseguradora vía API |
| Vinculación de tarjeta con un token | Flujo de consentimiento PSD2 (Tink, Salt Edge…) o card-linked offers |
| Secreto compartido en el webhook | Verificación de firma HMAC del proveedor, allowlist de IPs |
| Pago del comercio registrado a mano | Adeudos SEPA (mandato B2B) y conciliación bancaria |
| Lote CSV | Integración con la gestora (API/SFTP) y conciliación de participaciones |
| Tokens de sesión simples | OAuth2/OIDC, refresco, biometría en el dispositivo |
| SQLite | PostgreSQL + migraciones (Alembic) |

Pendiente para fases siguientes: compras online por afiliación, retos patrocinados, redondeos y aportaciones voluntarias, portal web para comercios, app nativa (Flutter/React Native) a partir del prototipo.
