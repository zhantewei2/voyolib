import asyncio
import time
from abc import ABC, abstractmethod
from typing import Optional

import aiomysql


def set_default_pool(pool: "YoConnPool"):
    global _default_pool
    _default_pool = pool


def get_default_pool() -> Optional["YoConnPool"]:
    return _default_pool


_default_pool: Optional["YoConnPool"] = None


class ConnPool(ABC):
    @abstractmethod
    async def get_conn(self):
        ...

    @abstractmethod
    async def release_conn(self, conn):
        ...


class ConnInfo:
    """One pooled connection: state machine ready <-> running, with expiry and type."""

    __slots__ = ("conn", "state", "conn_type", "expire_at")

    def __init__(self, conn, conn_type: str, max_timeout: float):
        self.conn = conn
        self.state = "ready"  # ready | running
        self.conn_type = conn_type  # core | burst
        self.expire_at = time.time() + max_timeout

    def is_expired(self) -> bool:
        return time.time() >= self.expire_at

    def refresh_expire(self, max_timeout: float):
        self.expire_at = time.time() + max_timeout


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
        self._core: list[ConnInfo] = []
        self._burst: list[ConnInfo] = []
        self._cond: asyncio.Condition = None
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def _ensure_init(self):
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            self._cond = asyncio.Condition()
            for _ in range(self._pool_size):
                conn = await self._connect()
                self._core.append(ConnInfo(conn, "core", self._max_timeout))
            self._initialized = True

    async def _connect(self):
        return await aiomysql.connect(**self._config)

    def _find(self, conn) -> Optional[ConnInfo]:
        for info in self._core + self._burst:
            if info.conn is conn:
                return info
        return None

    async def get_conn(self):
        await self._ensure_init()
        while True:
            async with self._cond:
                info = next((c for c in self._core if c.state == "ready"), None)
                if info is not None:
                    info.state = "running"
                elif len(self._burst) < self._max_burst:
                    info = ConnInfo(None, "burst", self._max_timeout)
                    info.state = "running"
                    self._burst.append(info)
                else:
                    await self._cond.wait()
                    continue

            # occupy-then-create: state already running, safe to await here
            if info.conn is None or info.conn.closed or info.is_expired():
                try:
                    await self._replace_conn(info)
                except Exception:
                    await self._abort_acquire(info)
                    raise
            return info.conn

    async def _replace_conn(self, info: ConnInfo):
        old = info.conn
        info.conn = await self._connect()
        info.refresh_expire(self._max_timeout)
        if old is not None:
            try:
                old.close()
            except Exception:
                pass

    async def _abort_acquire(self, info: ConnInfo):
        """Undo a failed acquire so the slot is not leaked."""
        async with self._cond:
            if info.conn_type == "burst":
                if info in self._burst:
                    self._burst.remove(info)
            else:
                info.state = "ready"
            self._cond.notify()

    async def release_conn(self, conn):
        info = self._find(conn)
        if info is None:
            try:
                conn.close()
            except Exception:
                pass
            return

        # rollback while still running: nobody else can hold this conn
        await self._safe_rollback(conn)

        async with self._cond:
            if info.conn_type == "burst":
                self._burst.remove(info)
            else:
                info.state = "ready"
            self._cond.notify()

        if info.conn_type == "burst":
            try:
                conn.close()
            except Exception:
                pass

    @staticmethod
    async def _safe_rollback(conn):
        """Rollback only when a transaction is still active (skip the extra RTT after commit)."""
        try:
            if not conn.closed and conn.get_transaction_status():
                await conn.rollback()
        except Exception:
            pass

    async def close(self):
        for info in self._core + self._burst:
            if info.conn is not None:
                try:
                    info.conn.close()
                except Exception:
                    pass
                info.conn = None
