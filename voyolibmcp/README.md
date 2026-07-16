# voyolibmcp

Python MCP Server，对外提供 voyo 工具文档查询，内部使用 `po-docs-db` 索引。

## 工具

| Tool | 作用 |
|------|------|
| `get_common_tool_doc` | 获取常规工具文档（`unique_id`、`logger`、`methods`） |
| `get_db_tool_doc` | 获取数据库工具文档（`mysql`、`oracle`、`sqlite`） |

## 启动

在根目录执行：

```bash
uv sync
uv run python -m voyolibmcp.seed
uv run python -m voyolibmcp.test
uv run voyolib-mcp
```

Seed 支持 `--clear` 先清空再写入。

数据库与文档目录默认位于 `voyolibmcp/.yo_ddb/`，相对于包目录解析。
