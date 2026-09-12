# app/storage.py
# Per-user list storage service with quota enforcement.

import json
import os
import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app import db
from app.plans import can_add_rows, can_create_list, can_upload_size, get_plan_limits

# Allow-list regex for generated filenames (mirrors the Streamlit helper).
_SAFE_FILENAME_RE = re.compile(r"[^\w\-. ()\[\]]")


def sanitize_name(name: str) -> str:
    """Turn an arbitrary user-supplied filename into a safe, flat filename.

    Mitigates path traversal: keeps only the basename (dropping ``../`` and
    absolute/backslash paths), replaces disallowed characters, strips leading
    dots (hidden files / ``..``), and guarantees a ``.json`` suffix.
    """
    base = os.path.basename((name or "").strip().replace("\\", "/"))
    base = _SAFE_FILENAME_RE.sub("_", base)
    base = re.sub(r"^\.+", "", base)
    if not base:
        base = "dados.json"
    if not base.lower().endswith(".json"):
        base += ".json"
    return base


def _session() -> Session:
    return db.get_session()


def _get_user_or_raise(session: Session, user_id: int) -> db.User:
    """Fetch a user, raising ValueError if missing."""
    user = session.query(db.User).filter_by(id=user_id).first()
    if user is None:
        raise ValueError("Usuário não encontrado")
    return user


async def count_lists(user_id: int) -> int:
    """Number of lists owned by ``user_id`` (used for quota checks)."""
    session = _session()
    try:
        return session.query(db.List).filter_by(user_id=user_id).count()
    finally:
        session.close()


async def create_list(user_id: int, name: str, data: List[dict]) -> db.List:
    """Create a list owned by ``user_id``, enforcing list-count and row quotas.

    Raises ValueError if a quota would be exceeded.
    """
    session = _session()
    try:
        user = _get_user_or_raise(session, user_id)
        ok, msg = await can_create_list(user)
        if not ok:
            raise ValueError(msg)
        limits = await get_plan_limits(user)
        ok, msg = await can_add_rows(user, len(data))
        if not ok:
            raise ValueError(msg)
        ok, msg = await can_upload_size(len(json.dumps(data).encode("utf-8")))
        if not ok:
            raise ValueError(msg)

        lst = db.List(
            user_id=user_id,
            name=name,
            data_json=json.dumps(data),
            row_limit=limits["rows"],
        )
        session.add(lst)
        session.commit()
        session.refresh(lst)
        return lst
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def get_lists(user_id: int) -> List[dict]:
    """Return one dict per list owned by ``user_id``."""
    session = _session()
    try:
        rows = session.query(db.List).filter_by(user_id=user_id).all()
        return [
            {
                "id": lst.id,
                "name": lst.name,
                "data": json.loads(lst.data_json or "[]"),
                "row_limit": lst.row_limit,
            }
            for lst in rows
        ]
    finally:
        session.close()


async def get_list(user_id: int, list_id: int) -> Optional[dict]:
    """Return a single list as a dict, only if owned by ``user_id``.

    Returns None if the list does not exist or belongs to another user.
    """
    session = _session()
    try:
        lst = session.query(db.List).filter_by(user_id=user_id, id=list_id).first()
        if lst is None:
            return None
        return {
            "id": lst.id,
            "name": lst.name,
            "data": json.loads(lst.data_json or "[]"),
            "row_limit": lst.row_limit,
        }
    finally:
        session.close()


async def update_list(user_id: int, list_id: int, data: List[dict]) -> None:
    """Replace a list's contents, only if owned by ``user_id``.

    Raises ValueError if the list is not owned or the row quota is exceeded.
    """
    session = _session()
    try:
        lst = session.query(db.List).filter_by(user_id=user_id, id=list_id).first()
        if lst is None:
            raise ValueError("Lista não encontrada ou sem permissão")
        user = _get_user_or_raise(session, user_id)
        ok, msg = await can_add_rows(user, len(data))
        if not ok:
            raise ValueError(msg)
        ok, msg = await can_upload_size(len(json.dumps(data).encode("utf-8")))
        if not ok:
            raise ValueError(msg)
        lst.data_json = json.dumps(data)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def delete_list(user_id: int, list_id: int) -> None:
    """Delete a list, only if owned by ``user_id``.

    Raises ValueError if the list does not exist or belongs to another user.
    """
    session = _session()
    try:
        lst = session.query(db.List).filter_by(user_id=user_id, id=list_id).first()
        if lst is None:
            raise ValueError("Lista não encontrada ou sem permissão")
        session.delete(lst)
        session.commit()
    finally:
        session.close()