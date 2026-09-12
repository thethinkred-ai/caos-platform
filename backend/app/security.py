import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from .config import get_settings

COOKIE_NAME = "caos_token"
REFRESH_COOKIE_NAME = "caos_refresh"

VERIFICATION_TOKEN_TTL = timedelta(hours=24)
RESET_TOKEN_TTL = timedelta(hours=1)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        # OAuth-only accounts have no password; password login is simply not possible.
        return False
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def make_email_token(purpose: str, ttl: timedelta) -> tuple[str, str]:
    """Return (raw_token, token_hash). The raw token goes into the email link,
    only its hash is stored in the database."""
    expires = int((datetime.now(UTC) + ttl).timestamp())
    raw = f"{purpose}:{expires}:{secrets.token_urlsafe(24)}"
    return raw, hash_email_token(raw)


def hash_email_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def is_valid_email_token(raw: str, purpose: str) -> bool:
    """Check purpose and expiry of a raw token (format 'purpose:expires:secret')."""
    try:
        token_purpose, expires, _ = raw.split(":", 2)
    except ValueError:
        return False
    return token_purpose == purpose and datetime.now(UTC).timestamp() < int(expires)


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    jti = secrets.token_hex(16)
    return jwt.encode({"sub": str(user_id), "exp": expires, "jti": jti, "type": "access"}, settings.jwt_secret, algorithm="HS256")


def create_refresh_token(user_id: int) -> str:
    settings = get_settings()
    expires = datetime.now(UTC) + timedelta(days=settings.refresh_token_days)
    jti = secrets.token_hex(16)
    return jwt.encode({"sub": str(user_id), "exp": expires, "jti": jti, "type": "refresh"}, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> int:
    payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token")
    return int(payload["sub"])


def decode_refresh_token(token: str) -> tuple[int, str]:
    payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    if payload.get("type") != "refresh":
        raise jwt.InvalidTokenError("Not a refresh token")
    return int(payload["sub"]), payload["jti"]


def get_cookie_settings() -> dict:
    settings = get_settings()
    is_https = "https" in settings.frontend_url
    return {
        "key": COOKIE_NAME,
        "httponly": True,
        "secure": is_https,
        "samesite": "lax",
        "path": "/",
        "max_age": settings.access_token_minutes * 60,
    }


def get_refresh_cookie_settings() -> dict:
    settings = get_settings()
    is_https = "https" in settings.frontend_url
    return {
        "key": REFRESH_COOKIE_NAME,
        "httponly": True,
        "secure": is_https,
        "samesite": "lax",
        "path": "/",
        "max_age": settings.refresh_token_days * 86400,
    }
