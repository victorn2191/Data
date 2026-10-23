from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from .db import init_db
from .routers import admin, merchants, users, webhooks

PROTOTYPE_DIR = Path(__file__).resolve().parents[2] / "app-prototype"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="FuturoYa – MVP de ahorro para la jubilación por consumo",
    version="0.1.0",
    lifespan=lifespan,
)
# En producción, limitar a los orígenes de la app
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(users.router)
app.include_router(merchants.public)
app.include_router(merchants.admin)
app.include_router(webhooks.router)
app.include_router(admin.router)


@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok"}


_SKELETON = (
    '<!doctype html><html lang="es"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
    "<style>body{margin:0}[hidden]{display:none!important}</style></head><body>{content}</body></html>"
)


@app.get("/app/", response_class=HTMLResponse, include_in_schema=False)
def prototype():
    """Prototipo de la app. El HTML es un fragmento (también se publica como artifact), así que se envuelve aquí."""
    return _SKELETON.replace("{content}", (PROTOTYPE_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/app/")
