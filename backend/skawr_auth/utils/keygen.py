"""
Key generation utilities for skawr-auth.

Generates cryptographically secure keys for:
- SKAWR_AUTH_SECRET_KEY (JWT signing — 64-char hex string)
- SKAWR_AUTH_STORE_ENCRYPTION_KEY (Fernet symmetric encryption for OAuth tokens)

Usage:
    # Generate both keys:
    python -m skawr_auth.utils.keygen

    # Generate only JWT secret:
    python -m skawr_auth.utils.keygen --jwt-only

    # Generate only encryption key:
    python -m skawr_auth.utils.keygen --encryption-only

    # Output as .env format:
    python -m skawr_auth.utils.keygen --env
"""

import secrets
import sys


def generate_jwt_secret(length: int = 64) -> str:
    """Generate a cryptographically secure JWT signing key.

    Returns a 64-character hex string (256 bits of entropy).
    Safe for HS256/HS384/HS512 algorithms.
    """
    return secrets.token_hex(length // 2)


def generate_fernet_key() -> str:
    """Generate a Fernet-compatible encryption key.

    Used for encrypting connected store OAuth tokens at rest.
    Returns a URL-safe base64-encoded 32-byte key.
    """
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()


def generate_all() -> dict[str, str]:
    """Generate all required keys for skawr-auth deployment.

    Returns:
        dict with keys:
            - SKAWR_AUTH_SECRET_KEY: JWT signing key
            - SKAWR_AUTH_STORE_ENCRYPTION_KEY: Fernet key for OAuth token encryption
    """
    return {
        "SKAWR_AUTH_SECRET_KEY": generate_jwt_secret(),
        "SKAWR_AUTH_STORE_ENCRYPTION_KEY": generate_fernet_key(),
    }


def main():
    """CLI entry point for key generation."""
    args = sys.argv[1:]

    jwt_only = "--jwt-only" in args
    encryption_only = "--encryption-only" in args
    env_format = "--env" in args

    if jwt_only:
        key = generate_jwt_secret()
        if env_format:
            print(f"SKAWR_AUTH_SECRET_KEY={key}")
        else:
            print(f"JWT Secret Key: {key}")
        return

    if encryption_only:
        key = generate_fernet_key()
        if env_format:
            print(f"SKAWR_AUTH_STORE_ENCRYPTION_KEY={key}")
        else:
            print(f"Store Encryption Key: {key}")
        return

    # Generate all keys
    keys = generate_all()

    if env_format:
        for name, value in keys.items():
            print(f"{name}={value}")
    else:
        print("=" * 60)
        print("  Skawr Auth — Generated Keys")
        print("=" * 60)
        print()
        print("Add these to your .env file on the VPS.")
        print("Both services (analytics + indexer) MUST use the same values.")
        print()
        for name, value in keys.items():
            print(f"  {name}={value}")
        print()
        print("=" * 60)
        print()
        print("Quick copy (pipe to clipboard):")
        print("  python -m skawr_auth.utils.keygen --env | pbcopy")


if __name__ == "__main__":
    main()
