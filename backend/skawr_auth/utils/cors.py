"""
CORS configuration utilities for Skawr Auth.

Provides environment-aware CORS origin resolution and a convenience
function to attach CORSMiddleware to any FastAPI app.
"""

import json
import os
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# Default origins by environment
_DEVELOPMENT_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3004",
    "http://localhost:8000",
    "http://localhost:8004",
]

_PRODUCTION_ORIGINS = [
    "https://analytics.ziyad.one",
    "https://analytics-api.ziyad.one",
    "https://skawr.com",
    "https://api.ziyad.one",
]


def get_allowed_origins() -> list[str]:
    """
    Resolve the list of allowed CORS origins.

    Priority:
    1. SKAWR_AUTH_ALLOWED_ORIGINS env var (JSON-encoded array) — if set, use it directly.
    2. Otherwise, derive defaults from the ENVIRONMENT env var:
       - "development", "local", or "test" → localhost origins
       - "production" → production domain origins
       - Anything else (unknown) → same as development (permissive for safety)
    """
    explicit = os.getenv("SKAWR_AUTH_ALLOWED_ORIGINS")
    if explicit:
        return json.loads(explicit)

    environment = os.getenv("ENVIRONMENT", "").lower()

    if environment == "production":
        return list(_PRODUCTION_ORIGINS)

    # development, local, test, or unknown — all get permissive localhost defaults
    return list(_DEVELOPMENT_ORIGINS)


def setup_cors_middleware(
    app: FastAPI,
    additional_origins: Optional[list[str]] = None,
) -> None:
    """
    Convenience function that adds CORSMiddleware to a FastAPI app.

    Merges get_allowed_origins() with any additional_origins passed in.
    Configures: allow_credentials=True, allow_methods=["*"], allow_headers=["*"].
    """
    origins = get_allowed_origins()

    if additional_origins:
        # Merge without duplicates, preserving order
        seen = set(origins)
        for origin in additional_origins:
            if origin not in seen:
                origins.append(origin)
                seen.add(origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
