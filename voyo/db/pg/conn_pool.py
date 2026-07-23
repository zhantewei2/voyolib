import asyncio
import logging
from typing import Any, Optional

import asyncpg

logger = logging.getLogger(__name__)

_default_pool: Optional["ConnectionPool"] = None


def set_default_pool(pool: "ConnectionPool") -> None:
    global _default_pool
    _default_pool = pool


def get_default_pool() -> Optional["ConnectionPool"]:
    return _default_pool


class ConnectionPool:
    """Async wrapper around asyncpg's native connection pool."""

    def __init__(
        self,
        dsn: str,
        *,
        min_size: int = 2,
        max_size: int = 10,
        max_inactive_lifetime: float = 300.0,
        **connect_kwargs: Any,
    ) -> None:
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._max_inactive_lifetime = max_inactive_lifetime
        self._connect_kwargs = connect_kwargs
        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()

    async def _ensure_open(self) -> None:
        if self._pool is not None:
            return
        async with self._lock:
            if self._pool is not None:
                return
            self._pool = await asyncpg.create_pool(
                dsn=self._dsn,
                min_size=self._min_size,
                max_size=self._max_size,
                max_inactive_connection_lifetime=self._max_inactive_lifetime,
                **self._connect_kwargs,
            )

    async def acquire(self) -> asyncpg.Connection:
        await self._ensure_open()
        return await self._pool.acquire()

    async def release(self, conn: asyncpg.Connection) -> None:
        if self._pool is None:
            raise RuntimeError("ConnectionPool is closed")
        await self._pool.release(conn)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


__all__ = ["ConnectionPool", "asyncpg", "set_default_pool", "get_default_pool"]
