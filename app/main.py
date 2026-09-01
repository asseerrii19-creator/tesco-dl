from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .database import Base, engine
from .routes import admin, api, assessment, auth, client, documents, field, home, intake, lab, lab_operations, management, operations, receiving, sampling_supervision
from .seed import seed

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
BARCODE_DIR = DATA_DIR / "barcodes"
for directory in (DATA_DIR, UPLOAD_DIR, BARCODE_DIR):
    directory.mkdir(parents=True, exist_ok=True)

APP_NAME = os.getenv("APP_NAME", "TSCO Digital Laboratory Platform")
APP_ENV = os.getenv("APP_ENV", "uat").strip().lower()
APP_SECRET = os.getenv("APP_SECRET", "development-only-change-me")
if APP_ENV == "production" and APP_SECRET == "development-only-change-me":
    raise RuntimeError("APP_SECRET must be replaced in production")

api_docs_enabled = os.getenv("ENABLE_API_DOCS", "true" if APP_ENV != "production" else "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    if APP_ENV != "production":
        Base.metadata.create_all(bind=engine)
    seed()
    yield


app = FastAPI(
    title=APP_NAME,
    version="2.6.0",
    lifespan=lifespan,
    docs_url="/docs" if api_docs_enabled else None,
    redoc_url=None,
    openapi_url="/openapi.json" if api_docs_enabled else None,
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.state.environment = APP_ENV

app.add_middleware(
    SessionMiddleware,
    secret_key=APP_SECRET,
    same_site="lax",
    https_only=APP_ENV == "production",
    max_age=8 * 60 * 60,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(self), geolocation=(self), microphone=()")
    response.headers.setdefault("Content-Security-Policy", "default-src 'self' data: blob:; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-src 'self'; frame-ancestors 'self'; connect-src 'self';")
    if request.url.path.startswith(("/login", "/admin", "/client", "/field", "/intake", "/receiving", "/lab", "/assessment", "/operations", "/sampling-supervision", "/management")):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(home.router)
app.include_router(field.router)
app.include_router(intake.router)
app.include_router(receiving.router)
app.include_router(lab.router)
app.include_router(lab_operations.router)
app.include_router(assessment.router)
app.include_router(operations.router)
app.include_router(sampling_supervision.router)
app.include_router(client.router)
app.include_router(documents.router)
app.include_router(management.router)
app.include_router(api.router)
