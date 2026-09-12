# tests/test_security_f05.py
# F0.5 (D4) security hardening tests:
#   - login sliding-window rate limit (10 falhas -> bloqueio 60s, per-IP)
#   - upload hard cap 10 MiB (413 semantics)
#   - filename sanitization against path traversal

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import db

db.configure_engine("sqlite:///:memory:")
db.create_all()

from app.auth import register, login
from app.ratelimit import LoginRateLimiter, LoginRateLimited
from app.plans import MAX_UPLOAD_BYTES, can_upload_size
from app.storage import sanitize_name, create_list, update_list


# ── Login rate limiter (unit) ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_limiter_allows_below_threshold():
    limiter = LoginRateLimiter(max_attempts=10, window_seconds=60)
    for _ in range(9):
        await limiter.record_failure("10.0.0.1")
    assert await limiter.is_blocked("10.0.0.1") is False
    assert await limiter.retry_after("10.0.0.1") == 0.0


@pytest.mark.asyncio
async def test_limiter_blocks_after_10_failures():
    limiter = LoginRateLimiter(max_attempts=10, window_seconds=60)
    for _ in range(10):
        await limiter.record_failure("10.0.0.1")
    assert await limiter.is_blocked("10.0.0.1") is True
    retry = await limiter.retry_after("10.0.0.1")
    assert 0 < retry <= 61


@pytest.mark.asyncio
async def test_limiter_is_per_ip():
    limiter = LoginRateLimiter(max_attempts=10, window_seconds=60)
    for _ in range(10):
        await limiter.record_failure("10.0.0.1")
    assert await limiter.is_blocked("10.0.0.2") is False


@pytest.mark.asyncio
async def test_limiter_success_clears_failures():
    limiter = LoginRateLimiter(max_attempts=10, window_seconds=60)
    for _ in range(8):
        await limiter.record_failure("10.0.0.1")
    await limiter.record_success("10.0.0.1")
    assert await limiter.is_blocked("10.0.0.1") is False


@pytest.mark.asyncio
async def test_limiter_window_slides_after_timeout():
    limiter = LoginRateLimiter(max_attempts=10, window_seconds=0.05)
    for _ in range(10):
        await limiter.record_failure("10.0.0.1")
    assert await limiter.is_blocked("10.0.0.1") is True
    await asyncio.sleep(0.06)
    assert await limiter.is_blocked("10.0.0.1") is False


# ── Login integration (rate limiter wired into auth.login) ─────────────────

@pytest.mark.asyncio
async def test_login_10_failures_then_blocked_even_with_right_password(monkeypatch):
    fresh = LoginRateLimiter(max_attempts=10, window_seconds=60)
    monkeypatch.setattr("app.auth.login_rate_limiter", fresh)

    await register("rl_user@example.com", "secret123")

    for _ in range(10):
        with pytest.raises(ValueError):
            await login("rl_user@example.com", "wrongpass", ip="192.168.1.10")

    with pytest.raises(LoginRateLimited):
        await login("rl_user@example.com", "secret123", ip="192.168.1.10")

    # A different IP is not affected and can still log in.
    user, token = await login("rl_user@example.com", "secret123", ip="192.168.1.11")
    assert user.email == "rl_user@example.com"
    assert token


@pytest.mark.asyncio
async def test_login_success_clears_counter(monkeypatch):
    fresh = LoginRateLimiter(max_attempts=10, window_seconds=60)
    monkeypatch.setattr("app.auth.login_rate_limiter", fresh)

    await register("rl_user2@example.com", "secret123")

    for _ in range(9):
        with pytest.raises(ValueError):
            await login("rl_user2@example.com", "wrongpass", ip="10.1.1.1")

    await login("rl_user2@example.com", "secret123", ip="10.1.1.1")
    # Counter cleared -> a fresh round of failures starts from zero.
    for _ in range(9):
        with pytest.raises(ValueError):
            await login("rl_user2@example.com", "wrongpass", ip="10.1.1.1")
    assert await fresh.is_blocked("10.1.1.1") is False


# ── Upload cap (10 MiB) ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_can_upload_size_boundary():
    ok, _ = await can_upload_size(MAX_UPLOAD_BYTES)
    assert ok is True
    ok, _ = await can_upload_size(MAX_UPLOAD_BYTES + 1)
    assert ok is False


@pytest.mark.asyncio
async def test_create_list_rejects_oversized_payload():
    user, _ = await register("big_upload@example.com", "secret123")
    oversized = [{"pad": "x" * (MAX_UPLOAD_BYTES + 1024)}]  # ~10 MiB
    with pytest.raises(ValueError) as exc:
        await create_list(user.id, "Big List", oversized)
    assert "10 MiB" in str(exc.value)


@pytest.mark.asyncio
async def test_update_list_rejects_oversized_payload():
    user, _ = await register("big_update@example.com", "secret123")
    lst = await create_list(user.id, "Small", [{"x": 1}])
    oversized = [{"pad": "y" * (MAX_UPLOAD_BYTES + 1024)}]
    with pytest.raises(ValueError) as exc:
        await update_list(user.id, lst.id, oversized)
    assert "10 MiB" in str(exc.value)


# ── Filename sanitization (path traversal) ─────────────────────────────────

def test_sanitize_name_strips_path_traversal():
    assert sanitize_name("../../etc/passwd") == "passwd.json"
    assert sanitize_name("..\\..\\secret.json") == "secret.json"
    assert sanitize_name("/etc/peakvault/data") == "data.json"


def test_sanitize_name_replaces_bad_chars():
    assert sanitize_name("my file (2).json") == "my file (2).json"
    assert sanitize_name("dados;mensal [v2]") == "dados_mensal [v2].json"
    assert sanitize_name("data") == "data.json"


def test_sanitize_name_empty_falls_back():
    assert sanitize_name("") == "dados.json"
    assert sanitize_name("..") == "dados.json"
    assert sanitize_name(None) == "dados.json"