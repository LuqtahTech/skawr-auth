"""
Centralized configuration for skawr-auth.

Provides a single source of truth for secret key resolution, algorithm selection,
and auth configuration across all consuming services (analytics, indexer, dashboard).

Environment variable priority chains ensure backward compatibility during migration
while converging on canonical SKAWR_AUTH_* prefixed variables.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

logger = logging.getLogger(__name__)

# Only for local development — production MUST set SKAWR_AUTH_SECRET_KEY
DEFAULT_SECRET_KEY = "your-secret-key-here-change-in-production"
DEFAULT_ALGORITHM = "HS256"


def _get_secret_key(override: Optional[str] = None) -> str:
    """
    Resolve the JWT signing secret key using a priority chain.

    Priority:
        1. override parameter (explicitly passed in)
        2. SKAWR_AUTH_SECRET_KEY env var (canonical)
        3. SECRET_KEY env var (legacy analytics compatibility)
        4. JWT_SECRET_KEY env var (legacy indexer compatibility)
        5. DEFAULT_SECRET_KEY constant (development only, logs a warning)

    Returns:
        The resolved secret key string.
    """
    if override:
        return override

    key = os.getenv("SKAWR_AUTH_SECRET_KEY")
    if key:
        return key

    key = os.getenv("SECRET_KEY")
    if key:
        return key

    key = os.getenv("JWT_SECRET_KEY")
    if key:
        return key

    logger.warning(
        "No secret key configured via SKAWR_AUTH_SECRET_KEY, SECRET_KEY, or JWT_SECRET_KEY. "
        "Using DEFAULT_SECRET_KEY — this is insecure and only suitable for development."
    )
    return DEFAULT_SECRET_KEY


def _get_algorithm(override: Optional[str] = None) -> str:
    """
    Resolve the JWT signing algorithm using a priority chain.

    Priority:
        1. override parameter (explicitly passed in)
        2. SKAWR_AUTH_ALGORITHM env var (canonical)
        3. ALGORITHM env var (legacy compatibility)
        4. Default "HS256"

    Returns:
        The resolved algorithm string.
    """
    if override:
        return override

    alg = os.getenv("SKAWR_AUTH_ALGORITHM")
    if alg:
        return alg

    alg = os.getenv("ALGORITHM")
    if alg:
        return alg

    return DEFAULT_ALGORITHM


@dataclass
class AuthConfig:
    """
    Complete auth configuration resolved from environment variables.

    All consuming services should use get_auth_config() to obtain this
    rather than reading env vars directly.
    """

    secret_key: str
    algorithm: str
    access_expire_minutes: int
    refresh_expire_days: int
    allowed_origins: List[str]
    legacy_token_deadline: Optional[date]


def get_auth_config(
    secret_key_override: Optional[str] = None,
    algorithm_override: Optional[str] = None,
) -> AuthConfig:
    """
    Build and return the complete auth configuration from environment variables.

    Environment variables read:
        - SKAWR_AUTH_SECRET_KEY / SECRET_KEY / JWT_SECRET_KEY (priority chain)
        - SKAWR_AUTH_ALGORITHM / ALGORITHM (priority chain)
        - SKAWR_AUTH_ACCESS_EXPIRE_MINUTES (default: 15)
        - SKAWR_AUTH_REFRESH_EXPIRE_DAYS (default: 30)
        - SKAWR_AUTH_ALLOWED_ORIGINS (JSON array, default: [])
        - SKAWR_AUTH_LEGACY_TOKEN_DEADLINE (ISO date string or empty, default: None)

    Args:
        secret_key_override: If provided, takes top priority for secret key.
        algorithm_override: If provided, takes top priority for algorithm.

    Returns:
        AuthConfig dataclass with all resolved values.
    """
    secret_key = _get_secret_key(secret_key_override)
    algorithm = _get_algorithm(algorithm_override)

    access_expire_minutes = int(
        os.getenv("SKAWR_AUTH_ACCESS_EXPIRE_MINUTES", "15")
    )
    refresh_expire_days = int(
        os.getenv("SKAWR_AUTH_REFRESH_EXPIRE_DAYS", "30")
    )

    # Parse allowed origins from JSON array
    origins_raw = os.getenv("SKAWR_AUTH_ALLOWED_ORIGINS", "")
    if origins_raw.strip():
        try:
            allowed_origins = json.loads(origins_raw)
            if not isinstance(allowed_origins, list):
                logger.warning(
                    "SKAWR_AUTH_ALLOWED_ORIGINS is not a JSON array, defaulting to empty list."
                )
                allowed_origins = []
        except json.JSONDecodeError:
            logger.warning(
                "SKAWR_AUTH_ALLOWED_ORIGINS is not valid JSON, defaulting to empty list."
            )
            allowed_origins = []
    else:
        allowed_origins = []

    # Parse legacy token deadline (ISO date or None)
    deadline_raw = os.getenv("SKAWR_AUTH_LEGACY_TOKEN_DEADLINE", "")
    legacy_token_deadline: Optional[date] = None
    if deadline_raw.strip():
        try:
            legacy_token_deadline = date.fromisoformat(deadline_raw.strip())
        except ValueError:
            logger.warning(
                f"SKAWR_AUTH_LEGACY_TOKEN_DEADLINE '{deadline_raw}' is not a valid ISO date, ignoring."
            )

    return AuthConfig(
        secret_key=secret_key,
        algorithm=algorithm,
        access_expire_minutes=access_expire_minutes,
        refresh_expire_days=refresh_expire_days,
        allowed_origins=allowed_origins,
        legacy_token_deadline=legacy_token_deadline,
    )
