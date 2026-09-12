# app/plans.py
# Quota and plan logic for PeakVault.

import json

from app import db

PLAN_LIMITS = {
    "free": {"lists": 1, "rows": 200},
    "pro": {"lists": 999, "rows": 10000},
    "lifetime": {"lists": 999, "rows": 10000},
}

# Hard safety cap on any single list payload (bytes), applied to every plan.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB


async def can_upload_size(size_bytes: int) -> tuple[bool, str]:
    """Check whether a payload fits the global 10 MiB upload cap.

    Returns (True, "OK") on success, or (False, <message>) when blocked.
    """
    if size_bytes > MAX_UPLOAD_BYTES:
        return False, "Upload exceeds the 10 MiB limit"
    return True, "OK"


async def get_plan_limits(user) -> dict:
    """Return the quota limits for a user's plan (defaults to free)."""
    plan = (user.plan or "free") if user else "free"
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def _count_lists_sync(user_id: int) -> int:
    """Number of lists owned by ``user_id``."""
    session = db.get_session()
    try:
        return session.query(db.List).filter_by(user_id=user_id).count()
    finally:
        session.close()


def _count_rows_sync(user_id: int) -> int:
    """Total rows across all lists owned by ``user_id``."""
    session = db.get_session()
    try:
        total = 0
        for lst in session.query(db.List).filter_by(user_id=user_id).all():
            total += len(json.loads(lst.data_json or "[]"))
        return total
    finally:
        session.close()


async def can_create_list(user) -> tuple[bool, str]:
    """Check whether the user may create a new list (list-count quota).

    Returns (True, "OK") on success, or (False, <message>) when blocked.
    """
    limits = await get_plan_limits(user)
    current = _count_lists_sync(user.id)
    if current >= limits["lists"]:
        return False, f"List quota exceeded (max {limits['lists']})"
    return True, "OK"


async def can_add_rows(user, new_row_count: int) -> tuple[bool, str]:
    """Check whether adding ``new_row_count`` rows stays within the row quota.

    Returns (True, "OK") on success, or (False, <message>) when blocked.
    """
    limits = await get_plan_limits(user)
    current = _count_rows_sync(user.id)
    if current + new_row_count > limits["rows"]:
        return False, f"Row quota exceeded (max {limits['rows']})"
    return True, "OK"