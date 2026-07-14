import contextvars
import functools
import inspect

from voyo.db.mysql.conn_pool import YoConnPool, get_default_pool

_tx_stack: contextvars.ContextVar[list] = contextvars.ContextVar("_tx_stack", default=[])


def _get_tx_stack() -> list:
    return _tx_stack.get()


class Transaction:

    def __init__(self, propagation="required", pool=None):
        if propagation not in ("required", "new"):
            raise ValueError("propagation must be 'required' or 'new'")
        self.propagation = propagation
        self.pool = pool or get_default_pool()
        if self.pool is None:
            raise RuntimeError(
                "No connection pool configured for @Transaction. "
                "Call set_default_pool(pool) first."
            )

    def __call__(self, func):
        if inspect.iscoroutinefunction(func):
            return self._wrap_async(func)
        raise TypeError("@Transaction now requires an async function")

    def _wrap_async(self, func):
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        has_conn_param = bool(params) and params[-1].name == "conn"

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            stack = _get_tx_stack()

            if stack and self.propagation != "new":
                conn = stack[-1]["conn"]
                if has_conn_param and "conn" not in kwargs:
                    kwargs["conn"] = conn
                return await func(*args, **kwargs)

            conn = await self.pool.get_conn()
            token = _tx_stack.set(stack + [{"conn": conn}])
            try:
                if has_conn_param and "conn" not in kwargs:
                    kwargs["conn"] = conn
                result = await func(*args, **kwargs)
                await conn.commit()
                return result
            except Exception:
                await conn.rollback()
                raise
            finally:
                _tx_stack.reset(token)
                await self.pool.release_conn(conn)

        return wrapper
