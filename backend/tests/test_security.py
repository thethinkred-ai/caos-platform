"""Unit tests for security primitives."""

from datetime import timedelta

from app.security import (
    VERIFICATION_TOKEN_TTL,
    hash_email_token,
    hash_password,
    is_valid_email_token,
    make_email_token,
    verify_password,
)


def test_verify_password_with_none_hash_returns_false():
    # Regression: OAuth-only accounts crashed password login with AttributeError.
    assert verify_password("some-password", None) is False


def test_verify_password_roundtrip():
    encoded = hash_password("strong-password-123")
    assert verify_password("strong-password-123", encoded) is True
    assert verify_password("wrong-password-123", encoded) is False


def test_verify_password_malformed_hash_returns_false():
    assert verify_password("x", "not-a-hash") is False


def test_email_token_format_purpose_and_expiry():
    raw, token_hash = make_email_token("verify", VERIFICATION_TOKEN_TTL)
    assert raw.startswith("verify:")
    assert token_hash == hash_email_token(raw)
    assert is_valid_email_token(raw, "verify") is True
    assert is_valid_email_token(raw, "reset") is False


def test_expired_email_token_rejected():
    raw, _ = make_email_token("verify", timedelta(seconds=-1))
    assert is_valid_email_token(raw, "verify") is False


def test_malformed_email_token_rejected():
    assert is_valid_email_token("garbage", "verify") is False
    assert is_valid_email_token("", "verify") is False
