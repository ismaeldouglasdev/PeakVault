# tests/test_foundation.py
# Tests for the PeakVault SaaS foundation layer (auth + storage + quotas).

import json
import sys
import os

# Ensure the project root is on the path (so `import app` works from tests).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

# Point the DB at an in-memory SQLite BEFORE importing the app modules.
from app import db

db.configure_engine("sqlite:///:memory:")
db.create_all()

from app.auth import register, login, get_user
from app.security import hash_password, verify_password
from app.storage import (
    create_list,
    get_lists,
    get_list,
    update_list,
    delete_list,
    count_lists,
)
from app.plans import get_plan_limits, can_create_list, can_add_rows


@pytest.mark.asyncio
async def test_register_creates_user_and_token():
    user, token = await register("ana@example.com", "secret123", "Ana")
    assert user.email == "ana@example.com"
    assert user.plan == "free"
    assert token  # non-empty JWT
    assert isinstance(token, str) and token.count(".") == 2


@pytest.mark.asyncio
async def test_register_duplicate_email_raises():
    await register("dup@example.com", "secret123")
    with pytest.raises(ValueError) as exc:
        await register("dup@example.com", "secret123")
    assert "already exists" in str(exc.value)


@pytest.mark.asyncio
async def test_register_invalid_email_raises():
    with pytest.raises(ValueError):
        await register("not-an-email", "secret123")


@pytest.mark.asyncio
async def test_register_short_password_raises():
    with pytest.raises(ValueError) as exc:
        await register("short@example.com", "abc")
    assert "Password too short" in str(exc.value)


@pytest.mark.asyncio
async def test_login_success():
    await register("login@example.com", "secret123")
    user, token = await login("login@example.com", "secret123")
    assert user.email == "login@example.com"
    assert token


@pytest.mark.asyncio
async def test_login_wrong_password_raises():
    await register("wrong@example.com", "secret123")
    with pytest.raises(ValueError) as exc:
        await login("wrong@example.com", "wrongpass")
    assert "Invalid credentials" in str(exc.value)


@pytest.mark.asyncio
async def test_login_case_insensitive_email():
    await register("CaseInsensitive@example.com", "secret123")
    user, _ = await login("caseinsensitive@EXAMPLE.com", "secret123")
    assert user.email == "caseinsensitive@example.com"


def test_hash_password_roundtrip():
    hashed = hash_password("my-secret-pass")
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password("my-secret-pass", hashed)
    assert not verify_password("wrong-pass", hashed)


def test_hash_password_random_salt():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # random salt -> different digests
    assert verify_password("same", h1) and verify_password("same", h2)


@pytest.mark.asyncio
async def test_create_list_ok():
    user, _ = await register("list@example.com", "secret123")
    data = [{"nome": "A", "nota": 9}, {"nome": "B", "nota": 8}]
    lst = await create_list(user.id, "Meus Animes", data)
    assert lst.id > 0
    assert lst.name == "Meus Animes"
    assert lst.row_limit == 200  # free plan default

    fetched = await get_list(user.id, lst.id)
    assert fetched is not None
    assert fetched["name"] == "Meus Animes"
    assert len(fetched["data"]) == 2


@pytest.mark.asyncio
async def test_list_isolation():
    user_a, _ = await register("a@example.com", "secret123")
    user_b, _ = await register("b@example.com", "secret123")

    lst_a = await create_list(user_a.id, "Lista A", [{"x": 1}])
    # user B cannot see user A's list
    assert await get_list(user_b.id, lst_a.id) is None
    # user B cannot update or delete it either
    with pytest.raises(ValueError):
        await update_list(user_b.id, lst_a.id, [{"x": 2}])
    with pytest.raises(ValueError):
        await delete_list(user_b.id, lst_a.id)


@pytest.mark.asyncio
async def test_quota_free_single_list():
    user, _ = await register("quota@example.com", "secret123")
    await create_list(user.id, "Lista 1", [{"x": 1}])
    # Second list blocked for free plan
    ok, msg = await can_create_list(user)
    assert ok is False
    assert "quota" in msg.lower()
    with pytest.raises(ValueError):
        await create_list(user.id, "Lista 2", [{"x": 1}])


@pytest.mark.asyncio
async def test_quota_free_200_rows():
    user, _ = await register("rows@example.com", "secret123")
    # 200 rows allowed
    data = [{"i": i} for i in range(200)]
    lst = await create_list(user.id, "200 Rows", data)
    assert len(getattr(lst, "data_json", "[]") or "[]") > 0

    # But updating to 201 rows is blocked
    with pytest.raises(ValueError):
        await update_list(user.id, lst.id, [{"i": i} for i in range(201)])


@pytest.mark.asyncio
async def test_quota_pro_unlimited():
    user, _ = await register("pro@example.com", "secret123")
    # Re-fetch inside an open session, upgrade to "pro", and capture the id
    # while the instance is still attached (commit expires ORM attributes and
    # the object returned by register() is detached).
    db_session = db.get_session()
    try:
        stored = db_session.query(db.User).filter_by(email="pro@example.com").first()
        stored.plan = "pro"
        db_session.commit()
        user_id = stored.id
    finally:
        db_session.close()

    for i in range(3):
        await create_list(user_id, f"Lista {i}", [{"x": i} for i in range(500)])
    assert await count_lists(user_id) == 3