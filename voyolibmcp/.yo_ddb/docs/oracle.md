# voyo Oracle

异步连接池 + 声明式事务，基于 `oracledb` 原生异步池与 `contextvars`。

## 快速开始

```python
from voyo.db.oracle import ConnectionPool, set_default_pool, transaction

pool = ConnectionPool(dsn="localhost:1521/ORCL", user="scott", password="tiger")
set_default_pool(pool)

@transaction
async def create_user(name: str, conn):
    async with conn.cursor() as cur:
        await cur.execute("INSERT INTO users (name) VALUES (:1)", [name])
```

函数最后一个参数名必须为 `conn`（禁止手动传递，由 ContextVar 自动注入事务连接）。

## 事务行为

- `@transaction` 方法执行完成后自动 **commit**（外层事务）。
- 方法抛出异常时自动 **rollback**（内层回滚到 SAVEPOINT），开发者无需 `try/finally`。
- 禁止手动向被 `@transaction` 标注的方法传递 `conn`，连接由上下文变量（ContextVar）管理，保证事务一致性。

## 嵌套事务

内层 `@transaction` 自动使用 SAVEPOINT，外层提交/回滚时统一处理：

```python
@transaction
async def create_user_with_log(name: str, conn):
    await create_user(name)  # 内层通过 SAVEPOINT 接入外层事务
    async with conn.cursor() as cur:
        await cur.execute("INSERT INTO logs (msg) VALUES (:1)", [f"created {name}"])
```

## 清理

```python
await pool.close()
```
