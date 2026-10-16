from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routers import admin, merchants, users, webhooks

PROTOTYPE_DIR = Path(__file__).resolve().parents[2] / "app-prototype"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Hucha Futura – MVP de ahorro para la jubilación por consumo",
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


if PROTOTYPE_DIR.exists():
    app.mount("/app", StaticFiles(directory=PROTOTYPE_DIR, html=True), name="app")

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/app/")
