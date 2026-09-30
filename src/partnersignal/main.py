"""Application factory: API, seeded fictional data, and the compiled React front end."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import clock
from .ai.service import Assistant
from .api.routes import router
from .config import get_settings
from .db import Base, SessionLocal, engine
from .models import Partner
from .seed import seed

STATIC = Path(__file__).with_name("static")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        if settings.reseed_on_start or session.query(Partner).count() == 0:
            seed(session, clock.today())
    app.state.seeded_on = clock.today()
    app.state.seed_lock = threading.Lock()
    app.state.assistant = Assistant(settings)
    yield


app = FastAPI(
    title="PartnerSignal API",
    version="2.0.0",
    description="Partner prospecting, qualification and follow-up workspace (fictional data).",
    lifespan=lifespan,
)
app.include_router(router)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if not request.url.path.startswith(("/docs", "/redoc", "/openapi")):
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; frame-ancestors 'none'",
        )
    return response


@app.post("/api/reset", include_in_schema=True, tags=["demo"])
def reset() -> dict:
    """Restore the fictional demo scenario."""
    with SessionLocal() as session:
        seed(session, clock.today())
    app.state.seeded_on = clock.today()
    return {"status": "reset"}


if (STATIC / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    candidate = (STATIC / path).resolve()
    if path and candidate.is_file() and STATIC.resolve() in candidate.parents:
        return FileResponse(candidate)
    index = STATIC / "index.html"
    if index.is_file():
        return FileResponse(index)
    return JSONResponse({"detail": "Front end not built. Run `npm run build` in frontend/."}, status_code=503)
