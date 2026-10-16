import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./hucha_mvp.db")
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "dev-admin-key")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "dev-webhook-secret")
    # Días que una aportación permanece pendiente (ventana de devoluciones)
    hold_days: int = int(os.getenv("HOLD_DAYS", "30"))
    # Proveedor del producto de ahorro (gestora / aseguradora)
    pension_provider: str = os.getenv("PENSION_PROVIDER", "demo-gestora")


settings = Settings()
