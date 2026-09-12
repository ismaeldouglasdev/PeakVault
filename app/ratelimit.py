# app/ratelimit.py
# Sliding-window per-IP login rate limiter (in-memory, thread-safe).
# Backed by an in-memory ring of failed-attempt timestamps per client IP.
# Swap to Redis later keeping the same interface for multi-instance production.

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Deque

logger = logging.getLogger(__name__)

# ── Defaults ───────────────────────────────────────────────────────────────

MAX_ATTEMPTS = 10       # max failed logins allowed inside the window
WINDOW_SECONDS = 60     # rolling window; reaching MAX_ATTEMPTS inside it blocks


class LoginRateLimited(Exception):
    """Raised when a client IP has exceeded the login failure threshold.

    Callers should map this to HTTP 429 and respect ``retry_after``.
    """

    def __init__(self, retry_after: float) -> None:
        self.retry_after = int(retry_after) + 1  # seconds until the next allowed attempt
        super().__init__(
            f"Too many failed login attempts. Retry in {self.retry_after}s."
        )


class LoginRateLimiter:
    """Sliding-window failed-login limiter, keyed by client IP.

    Tracks the timestamps of failed login attempts per IP. When the number
    of failures inside the rolling window reaches ``MAX_ATTEMPTS``, the IP is
    blocked until enough failures age out of the window.

    Usage::

        limiter = LoginRateLimiter()
        if await limiter.is_blocked("10.0.0.1"):
            raise LoginRateLimited(await limiter.retry_after("10.0.0.1"))
        # ... attempt login ...
        await limiter.record_failure("10.0.0.1")  # on invalid credentials
        await limiter.record_success("10.0.0.1")  # on successful login

    The current implementation is in-memory (single process). For production
    with many instances, swap the backend to Redis keeping the same interface.
    """

    def __init__(self, max_attempts: int = MAX_ATTEMPTS, window_seconds: float = WINDOW_SECONDS) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def is_blocked(self, ip: str) -> bool:
        """True if the IP has exhausted all allowed attempts within the window."""
        async with self._lock:
            self._prune(ip)
            return len(self._failures[ip]) >= self.max_attempts

    async def retry_after(self, ip: str) -> float:
        """Seconds until the oldest failure ages out of the window (0 if not blocked)."""
        async with self._lock:
            self._prune(ip)
            failures = self._failures[ip]
            if len(failures) < self.max_attempts:
                return 0.0
            oldest = failures[0]
            remaining = self.window_seconds - (time.time() - oldest)
            return max(remaining, 0.0)

    async def record_failure(self, ip: str) -> None:
        """Register a failed attempt for ``ip``."""
        now = time.time()
        async with self._lock:
            self._prune(ip)
            self._failures[ip].append(now)

    async def record_success(self, ip: str) -> None:
        """Clear any accumulated failures for ``ip`` after a successful login."""
        async with self._lock:
            self._failures.pop(ip, None)

    def _prune(self, ip: str) -> None:
        """Drop failures older than the window. Call while holding the lock."""
        cutoff = time.time() - self.window_seconds
        failures = self._failures[ip]
        while failures and failures[0] < cutoff:
            failures.popleft()
        if not failures:
            # Drop the empty key so blocked IPs that age out are forgotten.
            self._failures.pop(ip, None)


# Process-wide singleton used by the auth service.
login_rate_limiter = LoginRateLimiter()