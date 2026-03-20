from __future__ import annotations

"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables

# Import all models so SQLAlchemy knows about them
from app.models import user, organization, product, config, environment  # noqa: F401
from app.models import setting, targeting, segment, permission  # noqa: F401

# Import routers
from app.routers import (
    auth,
    organizations,
    products,
    configs,
    settings as settings_router,
    segments,
    sdk,
    audit_log,
    webhooks,
    tags,
    permissions,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables. Shutdown: cleanup."""
    await create_tables()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Feature flag and remote configuration management platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(products.router)
app.include_router(configs.config_router)
app.include_router(configs.env_router)
app.include_router(configs.sdk_key_router)
app.include_router(settings_router.router)
app.include_router(segments.router)
app.include_router(sdk.router)
app.include_router(audit_log.router)
app.include_router(webhooks.router)
app.include_router(tags.router)
app.include_router(permissions.router)


@app.get("/api/v1/health", tags=["Health"])
async def health():
    return {"status": "ok"}
