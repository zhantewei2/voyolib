# @voyo/docs-db-mcp

基于 [@voyo/docs-db](https://www.npmjs.com/package/@voyo/docs-db) 的文档知识库 MCP Server，为 `voyo/` lib 提供语义检索。

## 工作流

```
用户提问（如"如何使用 mysql"）
       │
       ▼
docs_query ──────► 返回 content = "voyo/db/mysql/README.md"（相对路径）
       │
       ▼
LLM Read ────────► 拿到 README.md 全文，生成回答
```

docs-db 仅索引关键词、返回相对路径；真实内容由 LLM 在运行时读取文件。

## 工具

| Tool | 作用 |
|------|------|
| `docs_write` | 写入文档 + 建索引 |
| `docs_query` | 关键词检索，返回路径列表 |
| `docs_list` | 列出文档 |
| `docs_delete` | 删除文档 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DOCS_DB_PATH` | `./.yo_ddb/data/docs.db` | SQLite 路径 |
| `DOCS_DB_DOCS_DIR` | `./.yo_ddb/docs` | Markdown 存放目录 |

## 启动

```bash
npm run build && node dist/index.js
```

## Seed（导入 voyo/ 文档索引）

```bash
# 写入 mysql / oracle / sqlite 三条索引
npm run seed

# 先清空再写入
npm run seed -- --clear
```

Seed 后对 `voyo/db/{mysql,oracle,sqlite}/` 下 README.md 的一句话描述会被索引；查询结果是文件相对路径，需配合 `Read` 工具获取全文。