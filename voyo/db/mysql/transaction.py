import functools
import inspect
import threading

from voyo.db.mysql.conn_pool import YoConnPool, get_default_pool

_tx_local = threading.local()

def _get_tx_stack():
    if not hasattr(_tx_local, "stack"):
        _tx_local.stack = []
    return _tx_local.stack

class Transaction:

    def __init__(self, propagation="required", pool=None):
        if propagation not in ("required", "new"):
            raise ValueError("propagation must be 'required' or 'new'")
        self.propagation = propagation
        self.pool = pool or get_default_pool()
        if self.pool is None:
            raise RuntimeError(
                "No connection pool configured for @Transaction. "
                "Call yo_mysql.set_default_pool(pool) first."
            )

    def __call__(self, func):
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        has_conn_param = bool(params) and params[-1].name == 'conn'

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            stack = _get_tx_stack()

            if stack and self.propagation != "new":
                conn = stack[-1]["conn"]

                if has_conn_param and "conn" not in kwargs:
                    kwargs["conn"] = conn

                return func(*args, **kwargs)

            conn = self.pool.get_conn()
            stack.append({"conn": conn})

            if has_conn_param and "conn" not in kwargs:
                kwargs["conn"] = conn
            try:
                result = func(*args, **kwargs)
                conn.commit()
                return result
            finally:
                conn.rollback()
                stack.pop()
                self.pool.release_conn(conn)

        return wrapper
