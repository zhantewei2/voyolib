import contextvars
import functools
import inspect
from typing import Optional

import aiosqlite

_db_config: Optional[dict] = None


def set_database(database: str, **connect_kwargs) -> None:
    global _db_config
    _db_config = {"database": database, **connect_kwargs}


def _get_db_config() -> dict:
    if _db_config is None:
        raise RuntimeError("No database configured. Call set_database() first.")
    return _db_config


_tx_stack: contextvars.ContextVar[list] = contextvars.ContextVar("_tx_stack", default=[])


def _get_tx_stack() -> list:
    return _tx_stack.get()


def get_current_connection() -> Optional[aiosqlite.Connection]:
    stack = _get_tx_stack()
    return stack[-1] if stack else None


async def _create_conn() -> aiosqlite.Connection:
    config = _get_db_config()
    conn = await aiosqlite.connect(**config)
    conn.row_factory = aiosqlite.Row
    return conn


class Transaction:

    def __init__(self, propagation: str = "required"):
        if propagation not in ("required", "new"):
            raise ValueError("propagation must be 'required' or 'new'")
        self.propagation = propagation

    def __call__(self, func):
        if inspect.iscoroutinefunction(func):
            return self._wrap_async(func)
        raise TypeError("@Transaction requires an async function")

    def _wrap_async(self, func):
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        has_conn_param = bool(params) and params[-1].name == "conn"

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            stack = _get_tx_stack()

            if stack and self.propagation != "new":
                conn = stack[-1]
                if has_conn_param and "conn" not in kwargs:
                    kwargs["conn"] = conn
                return await func(*args, **kwargs)

            conn = await _create_conn()
            token = _tx_stack.set(stack + [conn])

            if has_conn_param and "conn" not in kwargs:
                kwargs["conn"] = conn
            try:
                result = await func(*args, **kwargs)
                await conn.commit()
                return result
            except Exception:
                await conn.rollback()
                raise
            finally:
                _tx_stack.reset(token)
                await conn.close()

        return wrapper
