# 新增文档指南

voyolibmcp 通过 `po-docs-db` 建立关键词索引，`server.py` 按 type + lang + 关键词检索并返回文档内容。新增一个方法的文档，流程如下：

## 1. 写文档

在 `voyolibmcp/.yo_ddb/docs/` 下新建 `<doc_name>.md`，风格参考 `unique_id.md`：一句话说明 + import 示例 + 关键参数。

## 2. 注册种子

`seed.py` 的 `SEEDS` 加一条：

```python
{
    "type": "tool",        # 常规工具用 "tool"；数据库文档用 "python"
    "lang": "common",      # 常规工具用 "common"；数据库用 mysql/oracle/sqlite
    "question": "检索关键词",  # 决定能否被搜到，中英文别名都写上
    "doc_name": "xxx",      # 对应 docs/xxx.md
}
```

注意：`question` 是检索入口，调用方按 `tool_name` / `query` 搜索时匹配的是这里的分词，关键词不全会导致搜不到。

## 3. 同步 server.py 工具简介

`get_common_tool_doc`（或 `get_db_tool_doc`）的 docstring 中把新工具名加入列表，MCP 客户端靠这个简介发现可用工具。

## 4. 重建索引

```bash
uv run python -m voyolibmcp.seed --clear
```

`--clear` 先清空旧文档再全部写入，避免重复。索引存入 `.yo_ddb/data/docs.db`。

## 5. 验证

`test.py` 的 `cases` 加一条对应查询用例，然后执行：

```bash
uv run python -m voyolibmcp.test
```
