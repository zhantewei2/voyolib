from __future__ import annotations

import logging
import threading
import time
import weakref
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

try:
    import oracledb as oracle_driver
except ImportError:  # pragma: no cover
    try:
        import cx_Oracle as oracle_driver  # type: ignore
    except ImportError:
        oracle_driver = None  # type: ignore

logger = logging.getLogger(__name__)

_ORACLE_EMPTY_IS_NULL = True


@dataclass(frozen=True)
class PoolStats:
    opened: int
    borrowed: int
    available: int
    expired: int
    ping_failures: int
    max_lifetime_hits: int


class Row:
    __slots__ = ("_keys", "_values", "_lower_map")

    def __init__(self, cursor: Any, values: Sequence[Any]) -> None:
        self._values = tuple(values)
        self._keys = tuple(desc[0] for desc in getattr(cursor, "description", []) or [])
        self._lower_map = {k.lower(): i for i, k in enumerate(self._keys)}

    def __len__(self) -> int:
        return len(self._values)

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys)

    def __getitem__(self, key: Union[str, int]) -> Any:
        if isinstance(key, int):
            return self._values[key]
        try:
            return self._values[self._lower_map[key.lower()]]
        except KeyError as exc:
            raise KeyError(key) from exc

    def __getattr__(self, name: str) -> Any:
        try:
            return self._values[self._lower_map[name.lower()]]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> tuple[str, ...]:
        return self._keys

    def values(self) -> tuple[Any, ...]:
        return self._values

    def items(self) -> Iterator[tuple[str, Any]]:
        return zip(self._keys, self._values)

    def __repr__(self) -> str:
        return f"Row({dict(self.items())})"


class CursorWrapper:
    __slots__ = ("_cursor", "_row_factory")

    def __init__(self, cursor: Any, row_factory: Callable[[Any, Sequence[Any]], Any]) -> None:
        self._cursor = cursor
        self._row_factory = row_factory

    @staticmethod
    def _convert_positional_args(args: Optional[Sequence[Any]]) -> Optional[list[Any]]:
        if args is None:
            return None
        converted: list[Any] = []
        for value in args:
            if value == "" and _ORACLE_EMPTY_IS_NULL:
                converted.append(None)
            else:
                converted.append(value)
        return converted

    @staticmethod
    def _convert_keyword_args(kwargs: Optional[Mapping[str, Any]]) -> dict[str, Any]:
        if kwargs is None:
            return {}
        return {
            k: (None if (v == "" and _ORACLE_EMPTY_IS_NULL) else v)
            for k, v in kwargs.items()
        }

    @staticmethod
    def _set_clob_input_sizes(cursor: Any, params: Optional[Sequence[Any]]) -> None:
        if params is None or not hasattr(cursor, "setinputsizes"):
            return
        if oracle_driver is None:
            return
        sizes = []
        for value in params:
            if isinstance(value, str) and len(value) > 4000:
                sizes.append(oracle_driver.DB_TYPE_CLOB)
            else:
                sizes.append(None)
        if any(s is not None for s in sizes):
            try:
                cursor.setinputsizes(*sizes)
            except Exception as exc:  # pragma: no cover
                logger.warning("setinputsizes failed: %s", exc)

    def execute(self, sql: str, args: Optional[Sequence[Any]] = None, **kwargs: Any) -> "CursorWrapper":
        converted = self._convert_positional_args(args)
        converted_kw = self._convert_keyword_args(kwargs) if kwargs else None
        self._set_clob_input_sizes(self._cursor, converted)
        try:
            if converted_kw:
                self._cursor.execute(sql, converted_kw)
            else:
                self._cursor.execute(sql, converted or [])
        except Exception as exc:
            logger.debug("execute failed: %s | sql=%s", exc, sql[:200])
            raise
        return self

    def executemany(self, sql: str, argslist: Iterable[Optional[Sequence[Any]]]) -> "CursorWrapper":
        converted_list = [self._convert_positional_args(a) or [] for a in argslist]
        if converted_list:
            self._set_clob_input_sizes(self._cursor, converted_list[0])
        try:
            self._cursor.executemany(sql, converted_list)
        except Exception as exc:
            logger.debug("executemany failed: %s | sql=%s", exc, sql[:200])
            raise
        return self

    def fetchone(self) -> Optional[Any]:
        row = self._cursor.fetchone()
        if row is None:
            return None
        return self._row_factory(self._cursor, row)

    def fetchall(self) -> list[Any]:
        return [self._row_factory(self._cursor, row) for row in self._cursor.fetchall()]

    def fetchmany(self, size: Optional[int] = None) -> list[Any]:
        rows = self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()
        return [self._row_factory(self._cursor, row) for row in rows]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)

    def __iter__(self) -> Iterator[Any]:
        while True:
            row = self.fetchone()
            if row is None:
                break
            yield row


class _PooledConnection:
    __slots__ = ("_pool", "_conn", "_born", "_last_ping", "_in_use")

    def __init__(self, pool: "ConnectionPool", conn: Any) -> None:
        self._pool = weakref.ref(pool)
        self._conn = conn
        self._born = time.monotonic()
        self._last_ping = 0.0
        self._in_use = True

    def __del__(self) -> None:
        if self._in_use:
            try:
                self._conn.close()
            except Exception:
                pass

    @property
    def raw(self) -> Any:
        return self._conn

    def is_expired(self, max_lifetime: float) -> bool:
        return max_lifetime > 0 and (time.monotonic() - self._born) > max_lifetime

    def ping(self) -> bool:
        try:
            if hasattr(self._conn, "ping"):
                self._conn.ping()
            else:
                cursor = self._conn.cursor()
                try:
                    cursor.execute("SELECT 1 FROM DUAL")
                finally:
                    cursor.close()
            self._last_ping = time.monotonic()
            return True
        except Exception as exc:
            logger.debug("ping failed: %s", exc)
            return False

    def cursor(self) -> CursorWrapper:
        cursor = self._conn.cursor()
        return CursorWrapper(cursor, Row)

    def close(self) -> None:
        pool = self._pool()
        if pool is not None:
            pool._return_connection(self)
        else:
            self._destroy()

    def _destroy(self) -> None:
        self._in_use = False
        try:
            self._conn.close()
        except Exception as exc:
            logger.debug("error closing connection: %s", exc)


class ConnectionPool:
    def __init__(
        self,
        dsn: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
        *,
        min_size: int = 2,
        max_size: int = 10,
        increment: int = 1,
        max_lifetime: float = 3600.0,
        idle_timeout: float = 600.0,
        ping_interval: float = 60.0,
        leak_detection_timeout: float = 300.0,
        **connect_kwargs: Any,
    ) -> None:
        self._dsn = dsn
        self._user = user
        self._password = password
        self._connect_kwargs = connect_kwargs
        self._min_size = max(0, min_size)
        self._max_size = max(self._min_size, max_size)
        self._increment = max(1, increment)
        self._max_lifetime = max(0.0, max_lifetime)
        self._idle_timeout = max(0.0, idle_timeout)
        self._ping_interval = max(0.0, ping_interval)
        self._leak_detection_timeout = max(0.0, leak_detection_timeout)

        self._lock = threading.RLock()
        self._available: list[_PooledConnection] = []
        self._borrowed: set[_PooledConnection] = set()
        self._shutdown = False
        self._stats = {
            "expired": 0,
            "ping_failures": 0,
            "max_lifetime_hits": 0,
        }

        self._maybe_grow(self._min_size)
        self._start_maintenance()

    def _create_connection(self) -> Any:
        if oracle_driver is None:
            raise RuntimeError(
                "Oracle driver not installed; install 'oracledb' or 'cx_Oracle'"
            )
        logger.debug("creating new Oracle connection")
        return oracle_driver.connect(
            self._dsn,
            user=self._user,
            password=self._password,
            **self._connect_kwargs,
        )

    def _maybe_grow(self, target: int) -> None:
        with self._lock:
            current = len(self._available) + len(self._borrowed)
            to_create = min(target - current, self._max_size - current)
            for _ in range(max(0, to_create)):
                try:
                    conn = self._create_connection()
                except Exception:
                    logger.exception("failed to create Oracle connection")
                    raise
                self._available.append(_PooledConnection(self, conn))

    def acquire(self) -> _PooledConnection:
        if self._shutdown:
            raise RuntimeError("pool is shut down")

        with self._lock:
            while self._available:
                wrapper = self._available.pop()
                if wrapper.is_expired(self._max_lifetime):
                    wrapper._destroy()
                    self._stats["max_lifetime_hits"] += 1
                    continue
                if self._ping_interval > 0 and (
                    time.monotonic() - wrapper._last_ping > self._ping_interval
                ):
                    if not wrapper.ping():
                        wrapper._destroy()
                        self._stats["ping_failures"] += 1
                        continue
                wrapper._in_use = True
                self._borrowed.add(wrapper)
                return wrapper

            if len(self._borrowed) < self._max_size:
                self._maybe_grow(len(self._borrowed) + self._increment)
                if self._available:
                    wrapper = self._available.pop()
                    wrapper._in_use = True
                    self._borrowed.add(wrapper)
                    return wrapper

            raise RuntimeError("Oracle connection pool exhausted")

    def _return_connection(self, wrapper: _PooledConnection) -> None:
        with self._lock:
            wrapper._in_use = False
            self._borrowed.discard(wrapper)
            if self._shutdown or wrapper.is_expired(self._max_lifetime):
                wrapper._destroy()
                if wrapper.is_expired(self._max_lifetime):
                    self._stats["max_lifetime_hits"] += 1
                return
            if self._ping_interval > 0 and not wrapper.ping():
                wrapper._destroy()
                self._stats["ping_failures"] += 1
                return
            self._available.append(wrapper)

    @contextmanager
    def connection(self):
        wrapper = self.acquire()
        try:
            yield wrapper
        finally:
            wrapper.close()

    def _start_maintenance(self) -> None:
        self._maintenance_thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self._maintenance_thread.start()

    def _maintenance_loop(self) -> None:
        while not self._shutdown:
            time.sleep(min(30.0, self._idle_timeout / 2.0 or 30.0))
            self._maintenance_pass()

    def _maintenance_pass(self) -> None:
        now = time.monotonic()
        with self._lock:
            if self._idle_timeout > 0:
                kept: list[_PooledConnection] = []
                for wrapper in self._available:
                    if (
                        len(kept) >= self._min_size
                        and now - wrapper._last_ping > self._idle_timeout
                    ):
                        wrapper._destroy()
                    else:
                        kept.append(wrapper)
                self._available = kept

            if self._leak_detection_timeout > 0:
                for wrapper in self._borrowed:
                    if wrapper._in_use and now - wrapper._born > self._leak_detection_timeout:
                        logger.warning(
                            "possible connection leak: connection borrowed for %.0f seconds",
                            now - wrapper._born,
                        )

    def stats(self) -> PoolStats:
        with self._lock:
            return PoolStats(
                opened=len(self._available) + len(self._borrowed),
                borrowed=len(self._borrowed),
                available=len(self._available),
                expired=self._stats["expired"],
                ping_failures=self._stats["ping_failures"],
                max_lifetime_hits=self._stats["max_lifetime_hits"],
            )

    def close(self) -> None:
        self._shutdown = True
        with self._lock:
            for wrapper in self._available:
                wrapper._destroy()
            self._available.clear()
            for wrapper in list(self._borrowed):
                wrapper._destroy()
            self._borrowed.clear()

    def __del__(self) -> None:
        if not self._shutdown:
            self.close()


__all__ = [
    "ConnectionPool",
    "CursorWrapper",
    "Row",
    "PoolStats",
    "oracle_driver",
]
