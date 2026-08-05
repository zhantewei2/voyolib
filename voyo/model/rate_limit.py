"""Combined RPM pacing + concurrency limiter with auto-degradation on rate limit."""

import asyncio
import threading
import time
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

import httpx


class RateLimiter:
    """Smooth-pace outgoing requests at the given RPM and bound concurrency,
    with auto-degradation: a rate-limited response triggers a 30s hard block,
    drops rpm by 5 (floor 1), and schedules a 5-min recovery timer that bumps
    rpm back by 5 (ceiling = initial). Repeated rate limits within the wait
    window cancel and reschedule the timer, pushing recovery further out.
    """
    
    def __init__(
        self,
        *,
        rpm: int = 0,
        max_workers: int = 0,
        degrade_sleep: float = 30.0,
        degrade_step: int = 5,
        recover_wait: float = 300.0,
        min_rpm: int = 1,
    ) -> None:
        # RPM pacing
        self._initial_rpm = rpm
        self._current_rpm = rpm
        self._min_interval = 60.0 / rpm if rpm > 0 else 0.0
        self._last_req_at = 0.0
        # Concurrency caps
        self._sem: threading.Semaphore | None = (
            threading.Semaphore(max_workers) if max_workers > 0 else None
        )
        self._asem: asyncio.Semaphore | None = (
            asyncio.Semaphore(max_workers) if max_workers > 0 else None
        )
        # Degradation config
        self._degrade_sleep = degrade_sleep
        self._degrade_step = degrade_step
        self._recover_wait = recover_wait
        self._min_rpm = min_rpm
        # Degradation state
        self._blocked_until = 0.0
        self._recover_timer: threading.Timer | None = None
        # Single state lock covers pace + degradation mutations
        self._state_lock = threading.Lock()

    @contextmanager
    def acquire_sync(self) -> Generator[None]:
        if self._sem is not None:
            self._sem.acquire()
        try:
            self._pace_rpm_sync()
            yield
        finally:
            if self._sem is not None:
                self._sem.release()

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[None]:
        if self._asem is not None:
            await self._asem.acquire()
        try:
            await self._pace_rpm()
            yield
        finally:
            if self._asem is not None:
                self._asem.release()

    def is_rate_limited(self, resp: httpx.Response) -> bool:
        """Classify whether a response indicates rate limiting; on hit, auto-degrade.
        - 429 is always rate-limited
        - 500/503: read body and match "too many requests" (case-insensitive)
        - Other status codes return False
        """
        body = ""
        if resp.status_code in (500, 503):
            resp.read()
            body = resp.text
        return self.is_rate_limited_text(resp.status_code, body)

    def is_rate_limited_text(self, status_code: int, body: str) -> bool:
        """Same as is_rate_limited(resp), but takes primitives.
        Use when you only have status_code + body (e.g. from a caught exception)."""
        if status_code == 429:
            self._degrade()
            return True
        if status_code in (500, 503) and "too many requests" in body.lower():
            self._degrade()
            return True
        return False

    def _degrade(self) -> None:
        """Apply degradation: hard block next request + lower rpm + (re)schedule recovery."""
        with self._state_lock:
            self._blocked_until = time.monotonic() + self._degrade_sleep
            if self._initial_rpm > 0:
                self._current_rpm = max(self._current_rpm - self._degrade_step, self._min_rpm)
                self._min_interval = 60.0 / self._current_rpm
        if self._initial_rpm > 0:
            self._schedule_recovery()

    def _schedule_recovery(self) -> None:
        """Cancel any pending recovery timer and schedule a fresh one."""
        with self._state_lock:
            if self._recover_timer is not None:
                self._recover_timer.cancel()
            self._recover_timer = threading.Timer(self._recover_wait, self._recover)
            self._recover_timer.daemon = True
            self._recover_timer.start()

    def _recover(self) -> None:
        """Recovery callback fired by the timer: rpm += step, capped at initial."""
        with self._state_lock:
            self._recover_timer = None
            if self._initial_rpm <= 0:
                return
            self._current_rpm = min(self._current_rpm + self._degrade_step, self._initial_rpm)
            self._min_interval = 60.0 / self._current_rpm

    async def _pace_rpm(self) -> None:
        """Reserve a slot at max(last_req_at+min_interval, _blocked_until).
        Lock held only for the reservation; sleep runs outside the lock."""
        with self._state_lock:
            now = time.monotonic()
            if self._min_interval <= 0 and self._blocked_until <= now:
                return
            next_allowed = max(
                self._last_req_at + self._min_interval,
                self._blocked_until,
                now,
            )
            self._last_req_at = next_allowed
            wait = next_allowed - now
        if wait > 0:
            await asyncio.sleep(wait)

    def _pace_rpm_sync(self) -> None:
        """Sync version, same logic as _pace_rpm."""
        with self._state_lock:
            now = time.monotonic()
            if self._min_interval <= 0 and self._blocked_until <= now:
                return
            next_allowed = max(
                self._last_req_at + self._min_interval,
                self._blocked_until,
                now,
            )
            self._last_req_at = next_allowed
            wait = next_allowed - now
        if wait > 0:
            time.sleep(wait)
