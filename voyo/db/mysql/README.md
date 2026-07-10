# voyo MySQL

异步连接池 + 声明式事务，基于 `aiomysql` 与 `contextvars`。

## 快速开始

```python
from voyo.db.mysql.conn_pool import YoConnPool, set_default_pool
from voyo.db.mysql.transaction import Transaction

pool = YoConnPool(host="127.0.0.1", port=3306, user="root",
                  password="secret", database="test", pool_size=10)
set_default_pool(pool)

@Transaction
async def create_user(name: str, conn):
    async with conn.cursor() as cur:
        await cur.execute("INSERT INTO users (name) VALUES (%s)", (name,))
```

函数最后一个参数名必须为 `conn`（通过 kwargs 自动注入事务连接，禁止手动传递）。

## 事务行为

- `@Transaction` 方法执行完成后自动 **commit**。
- 方法抛出异常时自动 **rollback**，开发者无需 `try/finally`。
- 禁止手动向被 `@Transaction` 标注的方法传递 `conn`，连接由上下文变量（ContextVar）管理，保证事务一致性。

## 查询

默认使用 `DictCursor`，返回 `dict` 列表：

```python
@Transaction
async def get_user(user_id: int, conn):
    async with conn.cursor() as cur:
        await cur.execute("SELECT id, name FROM users WHERE id = %s", (user_id,))
        row = await cur.fetchone()
        # row == {"id": 1, "name": "alice"}

        await cur.execute("SELECT id, name FROM users")
        rows = await cur.fetchall()
        # rows == [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}]
```

## 传播机制

`propagation="required"`（默认）：嵌套调用复用同一连接，共享同一事务。

`propagation="new"`：始终开启新事务，独立提交/回滚。

## 清理

```python
await pool.close()
```
