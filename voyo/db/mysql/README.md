# voyo MySQL

异步连接池 + 声明式事务，基于 `aiomysql` 与 `contextvars`。

## 安装

```bash
pip install aiomysql
```

## 快速开始

### 1. 创建连接池

```python
from voyo.db.mysql.conn_pool import AsyncConnPool, set_default_pool

pool = AsyncConnPool(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="secret",
    database="test",
    pool_size=10,
    max_overflow=5,
    pool_recycle=3600,
)
set_default_pool(pool)
```

参数说明：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `host` | `localhost` | 数据库地址 |
| `port` | `3306` | 数据库端口 |
| `user` | `""` | 用户名 |
| `password` | `""` | 密码 |
| `database` | `""` | 库名 |
| `charset` | `utf8mb4` | 字符集 |
| `pool_size` | `10` | 池内常驻连接数 |
| `max_overflow` | `5` | 允许临时超出的最大连接数 |
| `pool_recycle` | `3600` | 连接最长存活秒数 |

### 2. 使用 `@Transaction`

`@Transaction` 装饰 `async def`，通过 `get_tx_conn()` 获取当前事务连接：

```python
from voyo.db.mysql.transaction import Transaction, get_tx_conn

@Transaction
async def create_user(name: str):
    conn = get_tx_conn()
    async with conn.cursor() as cur:
        await cur.execute("INSERT INTO users (name) VALUES (%s)", (name,))

@Transaction
async def create_user_with_log(name: str):
    await create_user(name)
    conn = get_tx_conn()
    async with conn.cursor() as cur:
        await cur.execute("INSERT INTO logs (msg) VALUES (%s)", (f"created {name}",))
```

### 3. 清理连接池

```python
async with pool:
    await create_user("alice")
# 或手动
await pool.close()
```

## 传播机制

`@Transaction(propagation="required")`（默认）：同一 `asyncio.Task` 内嵌套调用复用同一连接。

`@Transaction(propagation="new")`：始终开启新事务，独立于外层提交/回滚。

```python
@Transaction(propagation="new")
async def audit(action: str):
    conn = get_tx_conn()
    async with conn.cursor() as cur:
        await cur.execute("INSERT INTO audit (action) VALUES (%s)", (action,))
```

## 上下文传递原理

事务连接通过 `contextvars.ContextVar` 在协程间传递：

```mermaid
sequenceDiagram
    participant Caller
    participant LV as _tx_conn (ContextVar)
    participant Pool as AsyncConnPool

    Caller->>LV: required & has tx?
    alt 嵌套调用
        LV-->>Caller: existing conn
    else 新建事务
        Caller->>Pool: get_conn()
        Pool-->>Caller: conn
        Caller->>LV: set(conn)
        Note over Caller: func() executes
        alt success
            Caller->>conn: commit()
        else exception
            Caller->: rollback()
        end
        Caller->>LV: reset(token)
        Caller->>Pool: release_conn(conn)
    end
```

## 注意事项

- 所有数据库操作**必须使用参数化查询**（`%s` 占位符），禁止拼接 SQL。
- `@Transaction` 仅支持 `async def`，同步函数会因 `await` 失败。
- 事务上下文基于 `contextvars`，`await` / `asyncio.create_task` 均可正确传播；跨 `threading` 时上下文相互隔离。
- `pool_recycle` 秒后连接会被 aiomysql 自动回收重建，避免 MySQL `wait_timeout` 斩断连接。
- 应用启动时调用 `set_default_pool(pool)`，或在 `@Transaction(pool=...)` 中显式传入。
