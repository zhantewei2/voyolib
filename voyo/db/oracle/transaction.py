from __future__ import annotations

import contextvars
import functools
import inspect
import logging
import re
import uuid
from collections.abc import Callable
from typing import Any, Optional, TypeVar

import oracledb

from voyo.db.oracle.conn_pool import ConnectionPool, get_default_pool

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_SAVEPOINT_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_#$]*$", re.ASCII)

_tx_stack: contextvars.ContextVar[list] = contextvars.ContextVar("_tx_stack", default=[])


def _get_tx_stack() -> list:
    return _tx_stack.get()


def _generate_savepoint_name() -> str:
    return "SP_" + uuid.uuid4().hex[:16].upper()


def _validate_savepoint_name(name: str) -> None:
    if not _SAVEPOINT_NAME_RE.match(name):
        raise ValueError(f"invalid Oracle savepoint name: {name!r}")


def get_current_connection() -> Optional[oracledb.AsyncConnection]:
    stack = _get_tx_stack()
    return stack[-1] if stack else None


def transaction(pool: Optional[ConnectionPool] = None) -> Callable[[F], F]:
    if pool is None:
        pool = get_default_pool()
    if pool is None:
        raise RuntimeError(
            "No connection pool for @transaction. "
            "Pass pool= or call set_default_pool() first."
        )

    def decorator(func: F) -> F:
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        has_conn_param = bool(params) and params[-1].name == "conn"

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            stack = _get_tx_stack()
            is_nested = bool(stack)

            if is_nested:
                conn = stack[-1]
                savepoint_name = _generate_savepoint_name()
                _validate_savepoint_name(savepoint_name)
                async with conn.cursor() as cursor:
                    await cursor.execute(f"SAVEPOINT {savepoint_name}")
                logger.debug("created savepoint %s", savepoint_name)
                ctx = {"conn": conn, "savepoint": savepoint_name}
            else:
                conn = await pool.acquire()
                async with conn.cursor() as cursor:
                    await cursor.execute("BEGIN TRANSACTION")
                ctx = {"conn": conn, "savepoint": None}

            token = _tx_stack.set(stack + [conn])

            if has_conn_param and "conn" not in kwargs:
                kwargs["conn"] = conn
            try:
                result = await func(*args, **kwargs)
                async with conn.cursor() as cursor:
                    if ctx["savepoint"]:
                        await cursor.execute(f"RELEASE SAVEPOINT {ctx['savepoint']}")
                    else:
                        await conn.commit()
                return result
            except Exception:
                async with conn.cursor() as cursor:
                    if ctx["savepoint"]:
                        await cursor.execute(f"ROLLBACK TO SAVEPOINT {ctx['savepoint']}")
                        await cursor.execute(f"RELEASE SAVEPOINT {ctx['savepoint']}")
                    else:
                        await conn.rollback()
                raise
            finally:
                _tx_stack.reset(token)
                if not is_nested:
                    await pool.release(conn)

        return wrapper  # type: ignore[return-value]

    return decorator


__all__ = [
    "transaction",
    "get_current_connection",
]
