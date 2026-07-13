# voyolibmcp 重构工作点

## 目标
把 voyolibmcp 从一个直接暴露 docs CRUD 的 MCP 改为**对外提供文档查询服务**的 MCP：内部使用 PoDocsDB，外部只暴露两个工具。

## 工作点

1. **PoDocsDB 封装独立文件**
   - 新建 `voyolibmcp/po_docs.py`。
   - 在该文件中定义 `DEFAULT_DB_PATH` / `DEFAULT_DOCS_DIR`，使用 `Path(__file__).resolve().parent` 定位，路径以相对片段 `.yo_ddb/...` 组合，避免硬编码 `/Users/momo`。
   - 实例化并导出 `po_docs_db: PoDocsDB`，供 `server.py` 直接引用。

2. **新增常规工具文档**
   - 在 `voyolibmcp/.yo_ddb/docs/` 下新增：
     - `unique_id.md`：说明 `from voyo.utils import yo_unique` 与 `yo_unique.get_uid()`，保持简洁。
     - `logger.md`：说明 `from voyo.utils.logger.logger import init_logger`，在应用入口调用一次 `init_logger(...)`，之后使用标准 `logging.getLogger()`。

3. **重写 MCP server 工具**
   - 移除 `docs_write` / `docs_query` / `docs_list` / `docs_delete`。
   - 只保留两个工具：
     - `get_common_tool_doc(tool_name: str, query: str = "", limit: int = 3)`：查询 `type="tool" lang="common"`，按匹配结果读取文档内容并返回。
     - `get_db_tool_doc(db_type: str, query: str = "", limit: int = 3)`：查询 `type="python" lang=<mysql|oracle|sqlite>`，读取文档内容并返回。
   - 两个工具都调用 PoDocsDB 得到相对路径，再用该路径读取 `.md` 内容返回。

4. **更新 seed.py**
   - 数据源改为 `voyolibmcp/.yo_ddb/docs/`（相对当前模块）。
   - 索引 5 份文档：mysql、oracle、sqlite、unique_id、logger。
   - 清理旧文档逻辑保留。

5. **更新 test.py**
   - 改为验证两个新工具：分别查询常规工具和数据库工具，断言返回内容非空且包含关键信息。

6. **清理冗余配置（可选）**
   - 如 `config.py` 中的路径逻辑被 `po_docs.py` 完全覆盖，可考虑移除或保留作为兼容入口；本次先保留 `config.py` 但让 `po_docs.py` 自行解析路径，避免循环引用。

## 验收
- `uv run python -m voyolibmcp.seed` 成功写入 5 条文档。
- `uv run python -m voyolibmcp.test` 两个工具均返回对应 markdown 内容。
- `server.py` 仅暴露 `get_common_tool_doc` 与 `get_db_tool_doc`。
