from __future__ import annotations

import functools
import logging
import re
import threading
import uuid
from collections.abc import Callable
from typing import Any, Optional, TypeVar

from voyo.db.oracle.conn_pool import ConnectionPool, _PooledConnection

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_SAVEPOINT_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_#$]*$", re.ASCII)


class _TransactionContext:
    __slots__ = ("pool", "connection", "savepoint_name", "committed", "rolled_back")

    def __init__(
        self,
        pool: ConnectionPool,
        connection: _PooledConnection,
        savepoint_name: Optional[str] = None,
    ) -> None:
        self.pool = pool
        self.connection = connection
        self.savepoint_name = savepoint_name
        self.committed = False
        self.rolled_back = False


class _TransactionStack:
    def __init__(self) -> None:
        self._local = threading.local()

    def _get_stack(self) -> list[_TransactionContext]:
        if not hasattr(self._local, "stack"):
            self._local.stack = []
        return self._local.stack

    def current(self) -> Optional[_TransactionContext]:
        stack = self._get_stack()
        return stack[-1] if stack else None

    def push(self, ctx: _TransactionContext) -> None:
        self._get_stack().append(ctx)

    def pop(self) -> Optional[_TransactionContext]:
        stack = self._get_stack()
        return stack.pop() if stack else None

    def is_active(self) -> bool:
        return bool(self._get_stack())

    def depth(self) -> int:
        return len(self._get_stack())


_TRANSACTION_STACK = _TransactionStack()


def _generate_savepoint_name() -> str:
    return "SP_" + uuid.uuid4().hex[:16].upper()


def _validate_savepoint_name(name: str) -> None:
    if not _SAVEPOINT_NAME_RE.match(name):
        raise ValueError(f"invalid Oracle savepoint name: {name!r}")


def get_current_connection() -> Optional[_PooledConnection]:
    ctx = _TRANSACTION_STACK.current()
    return ctx.connection if ctx else None


def transaction(pool: ConnectionPool) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            outer_ctx = _TRANSACTION_STACK.current()
            is_nested = outer_ctx is not None

            if is_nested:
                conn = outer_ctx.connection
                if args and args[0] is conn:
                    call_args = args
                else:
                    call_args = (conn,) + args
                savepoint_name = _generate_savepoint_name()
                _validate_savepoint_name(savepoint_name)
                cursor = conn.cursor()
                cursor.execute(f"SAVEPOINT {savepoint_name}")
                logger.debug("created savepoint %s", savepoint_name)
                ctx = _TransactionContext(pool, conn, savepoint_name)
            else:
                conn = pool.acquire()
                call_args = (conn,) + args
                ctx = _TransactionContext(pool, conn, savepoint_name=None)

            _TRANSACTION_STACK.push(ctx)
            try:
                result = func(*call_args, **kwargs)
                if ctx.savepoint_name:
                    cursor = conn.cursor()
                    cursor.execute(f"RELEASE SAVEPOINT {ctx.savepoint_name}")
                    ctx.committed = True
                else:
                    conn.raw.commit()
                    ctx.committed = True
                return result
            except Exception:
                ctx.rolled_back = True
                try:
                    if ctx.savepoint_name:
                        cursor = conn.cursor()
                        cursor.execute(f"ROLLBACK TO SAVEPOINT {ctx.savepoint_name}")
                        cursor.execute(f"RELEASE SAVEPOINT {ctx.savepoint_name}")
                    else:
                        conn.raw.rollback()
                except Exception as rollback_exc:
                    logger.exception("rollback failed: %s", rollback_exc)
                raise
            finally:
                popped = _TRANSACTION_STACK.pop()
                if popped is not ctx:  # pragma: no cover
                    logger.error("transaction stack mismatch: expected %r, got %r", ctx, popped)
                if not is_nested:
                    conn.close()

        return wrapper  # type: ignore[return-value]

    return decorator


__all__ = [
    "transaction",
    "get_current_connection",
    "_TransactionContext",
    "_TransactionStack",
]
