import asyncio
import time
from typing import Optional

import aiomysql

_default_pool: Optional["AsyncConnPool"] = None


def set_default_pool(pool: "AsyncConnPool"):
    global _default_pool
    _default_pool = pool


def get_default_pool() -> Optional["AsyncConnPool"]:
    return _default_pool


class AsyncConnPool:
    def __init__(
        self,
        *,
        host: str = "localhost",
        port: int = 3306,
        user: str = "",
        password: str = "",
        database: str = "",
        charset: str = "utf8mb4",
        pool_size: int = 10,
        max_overflow: int = 5,
        pool_recycle: float = 3600,
    ):
        self._config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "db": database,
            "charset": charset,
            "autocommit": False,
        }
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._pool_recycle = pool_recycle
        self._created_at = time.monotonic()
        self._pool: Optional[aiomysql.Pool] = None

    async def _ensure_pool(self):
        if self._pool is None:
            self._pool = await aiomysql.create_pool(
                **self._config,
                minsize=self._pool_size,
                maxsize=self._pool_size + self._max_overflow,
                pool_recycle=self._pool_recycle,
            )

    async def get_conn(self):
        await self._ensure_pool()
        return await self._pool.acquire()

    async def release_conn(self, conn):
        self._pool.release(conn)

    async def close(self):
        if self._pool is not None:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def __aenter__(self):
        await self._ensure_pool()
        return self

    async def __aexit__(self, *args):
        await self.close()
