from abc import ABC, abstractmethod
import queue
import threading
import time
from typing import Optional

import pymysql

_default_pool: Optional["YoConnPool"] = None

def set_default_pool(pool: "YoConnPool"):
    global _default_pool
    _default_pool = pool

def get_default_pool() -> Optional["YoConnPool"]:
    return _default_pool

class ConnPool(ABC):

    @abstractmethod
    def get_conn(self):
        pass

    @abstractmethod
    def release_conn(self, conn):
        pass

class PooledConnection:

    def __init__(self, raw_conn, created_at: float, is_burst: bool = False):
        self.raw = raw_conn
        self.created_at = created_at
        self.is_burst = is_burst

    def is_expired(self, max_timeout: float) -> bool:
        return (time.time() - self.created_at) > max_timeout

    def close(self):
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
        database: str = "",
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
            "database": database,
            "charset": charset,
            "autocommit": False,
        }
        self._pool_size = pool_size
        self._max_burst = max_burst
        self._max_timeout = max_timeout
        self._pool = queue.Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._burst_lock = threading.Lock()
        self._burst_count = 0
        self._conn_map = {}

        for _ in range(pool_size):
            pooled = self._create_connection()
            self._pool.put(pooled)

    def _create_connection(self, is_burst: bool = False) -> PooledConnection:
        raw = pymysql.connect(**self._config)
        return PooledConnection(raw, time.time(), is_burst=is_burst)

    def _recycle(self, pooled: PooledConnection) -> PooledConnection:
        pooled.close()
        return self._create_connection()

    def get_conn(self):
        is_burst = False
        try:
            pooled = self._pool.get(block=False)
        except queue.Empty:

            with self._burst_lock:
                if self._burst_count < self._max_burst:
                    self._burst_count += 1
                    is_burst = True

            pooled = self._create_connection(is_burst=True)

        if not pooled.is_burst and pooled.is_expired(self._max_timeout):
            pooled = self._recycle(pooled)

        try:
            pooled.raw.ping()
        except Exception:
            pooled = self._recycle(pooled)

        with self._lock:
            self._conn_map[pooled.raw] = pooled
        return pooled.raw

    def release_conn(self, conn):
        with self._lock:
            pooled = self._conn_map.pop(conn, None)

        if pooled is None:

            try:
                conn.close()
            except Exception:
                pass
            return

        if pooled.is_burst:
            try:
                conn.rollback()
            except Exception:
                pass
            pooled.close()
            with self._burst_lock:
                self._burst_count = max(0, self._burst_count - 1)
            return

        try:
            conn.rollback()
        except Exception:
            pass

        try:
            self._pool.put(pooled, block=False)
        except queue.Full:
            pooled.close()
