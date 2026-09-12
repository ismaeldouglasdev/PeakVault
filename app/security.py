# app/security.py
# Auth helpers: PBKDF2-SHA256 password hashing (stdlib only) + HS256 JWT.

import hashlib
import hmac
import logging
import os
import secrets as _secrets
import warnings
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

logger = logging.getLogger(__name__)

# ── Password hashing (PBKDF2-SHA256, stdlib only) ─────────────
# Stored format: pbkdf2_sha256$<iterations>$<salt_hex>$<digest_hex>
_PBKDF2_ITERATIONS = 100_000
_PBKDF2_SALT_BYTES = 16

JWT_EXPIRES_SECONDS = 86400  # 24h
JWT_ALGORITHM = "HS256"

_ephemeral_jwt_secret: Optional[str] = None


def get_jwt_secret() -> str:
    """Resolve the JWT signing secret (env JWT_SECRET or ephemeral per-process).

    A single ephemeral secret is generated per process so tokens issued by
    login keep validating until restart. Production MUST set JWT_SECRET; a
    warning is logged once per process otherwise.
    """
    global _ephemeral_jwt_secret
    env_secret = os.getenv("JWT_SECRET")
    if env_secret:
        return env_secret
    if _ephemeral_jwt_secret is None:
        _ephemeral_jwt_secret = _secrets.token_urlsafe(48)
        logger.warning(
            "JWT_SECRET not configured; using EPHEMERAL per-process secret "
            "(tokens invalidate on every restart). Set JWT_SECRET in production."
        )
    return _ephemeral_jwt_secret


def hash_password(password: str) -> str:
    """Hash a plaintext password with PBKDF2-SHA256 (no passlib/bcrypt dep).

    Stored format: ``pbkdf2_sha256$<iterations>$<salt_hex>$<digest_hex>``.
    """
    salt = _secrets.token_bytes(_PBKDF2_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2 hash (constant-time)."""
    try:
        scheme, iterations_str, salt_hex, digest_hex = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def create_token(user_id: int) -> str:
    """Issue an HS256 token with sub=<user_id>, 24h expiry."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=JWT_EXPIRES_SECONDS),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> int:
    """Decode + validate a token; return the user_id.

    Raises jwt.InvalidTokenError (or subclass) if the token is expired,
    malformed, or signed with a different secret.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # PyJWT 2.x DeprecationWarning for weak algos
        payload = jwt.decode(
            token, get_jwt_secret(), algorithms=[JWT_ALGORITHM]
        )
    sub = payload.get("sub")
    try:
        return int(sub)
    except (TypeError, ValueError):
        raise jwt.InvalidTokenError("token 'sub' is not a valid user id")