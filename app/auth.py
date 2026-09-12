# app/auth.py
# Auth service: register, login, get_user.

import re
from typing import Optional

from sqlalchemy.orm import Session

from app import db
from app.ratelimit import LoginRateLimited, login_rate_limiter
from app.security import create_token, hash_password, verify_password


class User:
    def __init__(self, id, email, password_hash, plan, created_at, updated_at):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.plan = plan
        self.created_at = created_at
        self.updated_at = updated_at

async def register(email: str, password: str, name: str = "") -> tuple[db.User, str]:
    """Register a new user, returning (user, jwt_token).

    Raises:
        ValueError: If email format is invalid, password < 6 chars, or email already registered.
    """
    clean_email = (email or "").strip().lower()
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', clean_email):
        raise ValueError('Invalid email')
    if len(password) < 6:
        raise ValueError('Password too short')
    session: Session = db.get_session()
    try:
        existing = session.query(db.User).filter_by(email=clean_email).first()
        if existing:
            raise ValueError('Email already exists')
        pw_hash = hash_password(password)
        user = db.User(email=clean_email, password_hash=pw_hash, plan='free')
        session.add(user)
        session.commit()
        token = create_token(user.id)
        return user, token
    finally:
        session.close()

async def login(email: str, password: str, ip: Optional[str] = None) -> tuple[db.User, str]:
    """Authenticate an existing user, returning (user, jwt_token).

    When ``ip`` is provided, an IP-scoped sliding-window rate limiter guards
    against brute force: after MAX_ATTEMPTS failures inside the window, the IP
    is blocked (raises LoginRateLimited) until failures age out.

    Raises:
        ValueError: If credentials are invalid.
        LoginRateLimited: If the client IP exceeded the failure threshold.
    """
    clean_email = (email or "").strip().lower()
    if ip is not None and await login_rate_limiter.is_blocked(ip):
        raise LoginRateLimited(await login_rate_limiter.retry_after(ip))
    session: Session = db.get_session()
    try:
        user = session.query(db.User).filter_by(email=clean_email).first()
        if not user or not verify_password(password, user.password_hash):
            if ip is not None:
                await login_rate_limiter.record_failure(ip)
            raise ValueError('Invalid credentials')
        if ip is not None:
            await login_rate_limiter.record_success(ip)
        token = create_token(user.id)
        session.expunge(user)
        return user, token
    finally:
        session.close()

async def get_user(user_id: int) -> Optional[db.User]:
    session: Session = db.get_session()
    try:
        return session.query(db.User).filter_by(id=user_id).first()
    finally:
        session.close()