# app/db.py
# SQLAlchemy 2.0 sync database layer (sqlite3 driver for local dev).
# Swap to Postgres later via DATABASE_URL only.

import os
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

DEFAULT_DATABASE_URL = "sqlite:///./data/peakvault.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


class Base(DeclarativeBase):
    """Declarative base for all PeakVault ORM models."""


# Engine + session factory are constructed lazily so tests can re-point
# DATABASE_URL before the first access.
_engine = None
_SessionLocal = None


def _utcnow() -> datetime:
    """Timezone-aware UTC now, stored as naive UTC in SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_engine():
    """Return the configured SQLAlchemy engine, building it on first use.

    Uses sqlite3 (sync) by default. For Postgres swap DATABASE_URL to e.g.
    ``postgresql+psycopg2://...`` and this layer keeps working unchanged.
    """
    global _engine
    if _engine is None:
        connect_args = {}
        if DATABASE_URL.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        _engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
    return _engine


def get_session_factory():
    """Return a sessionmaker bound to the configured engine."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autocommit=False, autoflush=False, future=True
        )
    return _SessionLocal


def get_session() -> Session:
    """Return a new ORM session (context-manager friendly).

    Usage::

        with get_session() as session:
            session.add(user)
            session.commit()
    """
    return get_session_factory()()


def configure_engine(url: str) -> None:
    """Re-point the engine/session factory at a different database.

    Used by tests (in-memory SQLite) and at startup to honour DATABASE_URL
    changes made after module import.
    """
    global _engine, _SessionLocal, DATABASE_URL
    DATABASE_URL = url
    _engine = None
    _SessionLocal = None
    get_engine()


def ensure_data_dir() -> None:
    """Create the ./data directory if it does not exist (SQLite file path)."""
    data_dir = os.path.dirname(
        DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
    )
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)


class User(Base):
    """A PeakVault account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(32), default="free", nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    lists: Mapped[list["List"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User id={self.id} email={self.email!r} plan={self.plan!r}>"


class List(Base):
    """A user-owned list, with its row contents stored as a JSON string."""

    __tablename__ = "lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    row_limit: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="lists")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<List id={self.id} user_id={self.user_id} name={self.name!r} rows=...>"


def create_all() -> None:
    """Create all tables (idempotent). Called on startup."""
    ensure_data_dir()
    Base.metadata.create_all(get_engine())