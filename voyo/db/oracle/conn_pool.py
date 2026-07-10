import logging
from typing import Any, Optional

import oracledb

logger = logging.getLogger(__name__)

_default_pool: Optional["ConnectionPool"] = None


def set_default_pool(pool: "ConnectionPool") -> None:
    global _default_pool
    _default_pool = pool


def get_default_pool() -> Optional["ConnectionPool"]:
    return _default_pool


class ConnectionPool:
    """Async wrapper around oracledb's native async connection pool."""

    def __init__(
        self,
        dsn: str,
        *,
        min_size: int = 2,
        max_size: int = 10,
        increment: int = 1,
        max_lifetime: float = 3600.0,
        ping_interval: float = 60.0,
        **connect_kwargs: Any,
    ) -> None:
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._increment = increment
        self._max_lifetime = max_lifetime
        self._ping_interval = ping_interval
        self._connect_kwargs = connect_kwargs
        self._pool: Optional[oracledb.AsyncConnectionPool] = None

    async def _ensure_open(self) -> None:
        if self._pool is not None:
            return
        self._pool = await oracledb.create_pool_async(
            dsn=self._dsn,
            min=self._min_size,
            max=self._max_size,
            increment=self._increment,
            max_lifetime_session=self._max_lifetime,
            ping_interval=int(self._ping_interval),
            **self._connect_kwargs,
        )

    async def acquire(self) -> oracledb.AsyncConnection:
        await self._ensure_open()
        return await self._pool.acquire()

    async def release(self, conn: oracledb.AsyncConnection) -> None:
        await self._pool.release(conn)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


__all__ = ["ConnectionPool", "oracledb"]
