"""FastAPI application — mounts the four route packages.

Run locally:
    uvicorn onehealth_agents.api:app --reload --port 8000

In production the same module deploys behind a uvicorn worker pool
fronted by an HTTPS terminator. CORS is open to the published
GitHub Pages origin; tighten in production.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import auth, context, profile, reports

app = FastAPI(
    title="AZ One Health Sentinel Intake API",
    version="0.1.0",
    description=(
        "Anonymous-first Human / Animal / Environmental reporting "
        "with optional account-attached follow-up. The OpenAPI spec "
        "at api/openapi.yaml is normative; this implementation is one "
        "conformant backend."
    ),
    openapi_url="/v1/openapi.json",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
)

# The pilot is served from GitHub Pages; the dev origin is :3000.
# Production deployment should set ONEHEALTH_CORS_ALLOWED_ORIGINS
# to the exact deploy origin(s), comma-separated.
_default_origins = "http://localhost:3000,https://tyson-swetnam.github.io"
_origins = [
    o.strip()
    for o in os.environ.get("ONEHEALTH_CORS_ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(reports.router, prefix="/v1")
app.include_router(profile.router, prefix="/v1")
app.include_router(context.router, prefix="/v1")
app.include_router(auth.router, prefix="/v1")


@app.get("/v1/healthz", tags=["meta"])
def healthz() -> dict[str, str]:
    return {
        "status": "ok",
        "build": os.environ.get("ONEHEALTH_BUILD", "dev"),
    }
