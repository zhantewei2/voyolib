# voyo SQLite

异步声明式事务，基于 `aiosqlite` 与 `contextvars`。SQLite 为文件数据库，无需连接池。

## 快速开始

```python
from voyo.db.sqlite import set_database, Transaction

set_database("app.db")

@Transaction
async def create_user(name: str, conn):
    await conn.execute("INSERT INTO users (name) VALUES (?)", (name,))
```

函数最后一个参数名必须为 `conn`（禁止手动传递，由 ContextVar 自动注入事务连接）。

## 事务行为

- `@Transaction` 方法执行完成后自动 **commit**。
- 方法抛出异常时自动 **rollback**，开发者无需 `try/finally`。
- 禁止手动向被 `@Transaction` 标注的方法传递 `conn`，连接由上下文变量（ContextVar）管理，保证事务一致性。

## 传播机制

`propagation="required"`（默认）：嵌套调用复用同一连接。

`propagation="new"`：始终开启新事务，独立提交/回滚。
