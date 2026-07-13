# voyolib

Python library for Voyo.

## MCP 配置

安装本依赖后，可在 Agent 的 MCP 配置中添加 `voyolib-mcp`：

```json
{
  "mcpServers": {
    "voyollib-mcp": {
      "command": "uv",
      "args": ["run", "voyolib-mcp"],
      "env": {}
    }
  }
}
```

配置后即可使用 `get_common_tool_doc` 与 `get_db_tool_doc` 两个工具查询 voyo 文档。
