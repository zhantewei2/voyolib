import asyncio
import time
from abc import ABC, abstractmethod
from typing import Optional

import aiomysql

_default_pool: Optional["YoConnPool"] = None


def set_default_pool(pool: "YoConnPool"):
    global _default_pool
    _default_pool = pool


def get_default_pool() -> Optional["YoConnPool"]:
    return _default_pool


class ConnPool(ABC):

    @abstractmethod
    async def get_conn(self):
        pass

    @abstractmethod
    async def release_conn(self, conn):
        pass


class PooledConnection:

    def __init__(self, raw_conn, created_at: float, is_burst: bool = False):
        self.raw = raw_conn
        self.created_at = created_at
        self.is_burst = is_burst

    def is_expired(self, max_timeout: float) -> bool:
        return (time.time() - self.created_at) > max_timeout

    async def close(self):
        if self.raw:
            try:
                self.raw.close()
            except Exception:
                pass
            self.raw = None


class YoConnPool(ConnPool):

    def __init__(
        self,
        *,
        host: str = "localhost",
        port: int = 3306,
        user: str = "",
        password: str = "",
        db: str = "",
        charset: str = "utf8mb4",
        pool_size: int = 5,
        max_burst: int = 10,
        max_timeout: float = 600,
    ):
        self._config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "db": db,
            "charset": charset,
            "autocommit": False,
            "cursorclass": aiomysql.DictCursor,
        }
        self._pool_size = pool_size
        self._max_burst = max_burst
        self._max_timeout = max_timeout
        self._pool: asyncio.Queue = None
        self._lock = asyncio.Lock()
        self._burst_lock = asyncio.Lock()
        self._burst_count = 0
        self._conn_map = {}
        self._initialized = False

    async def _ensure_init(self):
        if self._initialized:
            return
        async with self._lock:
            if self._initialized:
                return
            self._pool = asyncio.Queue(maxsize=self._pool_size)
            for _ in range(self._pool_size):
                pooled = await self._create_connection()
                self._pool.put_nowait(pooled)
            self._initialized = True

    async def _create_connection(self, is_burst: bool = False) -> PooledConnection:
        raw = await aiomysql.connect(**self._config)
        return PooledConnection(raw, time.time(), is_burst=is_burst)

    async def _recycle(self, pooled: PooledConnection) -> PooledConnection:
        await pooled.close()
        return await self._create_connection()

    async def get_conn(self):
        await self._ensure_init()

        is_burst = False
        try:
            pooled = self._pool.get_nowait()
        except asyncio.QueueEmpty:
            async with self._burst_lock:
                if self._burst_count < self._max_burst:
                    self._burst_count += 1
                    is_burst = True
            pooled = await self._create_connection(is_burst=True)

        if not pooled.is_burst and pooled.is_expired(self._max_timeout):
            pooled = await self._recycle(pooled)

        try:
            await pooled.raw.ping()
        except Exception:
            pooled = await self._recycle(pooled)

        async with self._lock:
            self._conn_map[pooled.raw] = pooled
        return pooled.raw

    async def release_conn(self, conn):
        async with self._lock:
            pooled = self._conn_map.pop(conn, None)

        if pooled is None:
            try:
                conn.close()
            except Exception:
                pass
            return

        if pooled.is_burst:
            try:
                await conn.rollback()
            except Exception:
                pass
            await pooled.close()
            async with self._burst_lock:
                self._burst_count = max(0, self._burst_count - 1)
            return

        try:
            await conn.rollback()
        except Exception:
            pass

        try:
            self._pool.put_nowait(pooled)
        except asyncio.QueueFull:
            await pooled.close()

    async def close(self):
        if self._pool:
            while not self._pool.empty():
                pooled = self._pool.get_nowait()
                await pooled.close()
        for pooled in self._conn_map.values():
            await pooled.close()
        self._conn_map.clear()
