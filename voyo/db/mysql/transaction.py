import contextvars
import functools
from typing import Optional

import aiomysql

from .conn_pool import _default_pool, get_default_pool

_tx_conn: contextvars.ContextVar[Optional[aiomysql.Connection]] = contextvars.ContextVar(
    "_tx_conn", default=None
)


def get_tx_conn() -> Optional[aiomysql.Connection]:
    return _tx_conn.get()


class Transaction:
    def __init__(self, propagation="required", pool=None):
        if propagation not in ("required", "new"):
            raise ValueError("propagation must be 'required' or 'new'")
        self.propagation = propagation
        self.pool = pool

    def __call__(self, func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            outer = _tx_conn.get()

            if outer is not None and self.propagation != "new":
                token = None
                new_conn = False
                conn = outer
            else:
                pool = self.pool or get_default_pool()
                if pool is None:
                    raise RuntimeError(
                        "No connection pool configured. "
                        "Call set_default_pool(pool) first."
                    )
                conn = await pool.get_conn()
                token = _tx_conn.set(conn)
                new_conn = True

            try:
                result = await func(*args, **kwargs)
                if new_conn:
                    await conn.commit()
                return result
            except Exception:
                if new_conn:
                    await conn.rollback()
                raise
            finally:
                if new_conn:
                    _tx_conn.reset(token)
                    await pool.release_conn(conn)

        return wrapper
