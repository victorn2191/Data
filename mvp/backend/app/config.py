import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./futuroya_mvp.db")
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "dev-admin-key")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "dev-webhook-secret")
    # Días que una aportación permanece pendiente (ventana de devoluciones)
    hold_days: int = int(os.getenv("HOLD_DAYS", "30"))
    # Proveedor del producto de ahorro (gestora / aseguradora)
    pension_provider: str = os.getenv("PENSION_PROVIDER", "demo-gestora")
    # Moneda de operación (córdobas) y tasa para mostrar el equivalente en dólares
    currency: str = os.getenv("CURRENCY", "NIO")
    usd_rate: float = float(os.getenv("USD_RATE", "37.10"))  # C$ por cada US$ 1


settings = Settings()


def to_usd_cents(nio_cents: int) -> int:
    """Equivalente en centavos de dólar de un importe en centavos de córdoba."""
    return round(nio_cents / settings.usd_rate)
