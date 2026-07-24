"""voyolibmcp stdio MCP server — 对外提供 voyo 工具文档查询。"""

from __future__ import annotations

import json
import traceback
from typing import Any

from mcp.server.fastmcp import FastMCP

from voyolibmcp.po_docs import po_docs_db, read_doc

mcp = FastMCP("voyolibmcp")


def _ok(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, ensure_ascii=False, indent=2)


def _fetch_docs(type_: str, lang: str, query: str, limit: int) -> dict[str, Any]:
    """查询 PoDocsDB 并读取匹配文档内容。"""
    search_query = f"{lang} {query}".strip()
    result = po_docs_db.query(type=type_, lang=lang, query=search_query, limit=limit)
    return {
        "results": [
            {
                "id": item.id,
                "question": item.question,
                "doc_path": item.doc_path,
                "content": item.content or read_doc(item.doc_path),
            }
            for item in result.results
        ]
    }


@mcp.tool()
def get_common_tool_doc(tool_name: str = "", query: str = "", limit: int = 3) -> str:
    """获取常规工具文档（unique_id / logger / methods）。

    Args:
        tool_name: 工具名，如 unique_id、logger 或 methods；为空时按 query 搜索。
        query: 额外查询关键词。
        limit: 返回文档数量上限。
    """
    try:
        search = f"{tool_name} {query}".strip()
        return _ok(_fetch_docs(type_="tool", lang="common", query=search, limit=limit))
    except Exception as e:
        return _err(f"{e}\n{traceback.format_exc()}")


@mcp.tool()
def get_ai_tool_doc(tool_name: str = "", query: str = "", limit: int = 3) -> str:
    """获取 AI 工具文档：大模型对话（openai）、文本向量嵌入（embedding）、文本分块（chunk）。

    Args:
        tool_name: 工具名，openai（兼容 OpenAI 格式的 LLM 接口）、embedding（向量嵌入）、chunk（按 token 切分文本）；为空时按 query 搜索。
        query: 额外查询关键词。
        limit: 返回文档数量上限。
    """
    try:
        search = f"{tool_name} {query}".strip()
        return _ok(_fetch_docs(type_="tool", lang="common", query=search, limit=limit))
    except Exception as e:
        return _err(f"{e}\n{traceback.format_exc()}")


@mcp.tool()
def get_db_tool_doc(db_type: str, query: str = "", limit: int = 3) -> str:
    """获取数据库工具文档（mysql / oracle / sqlite / pg）。

    Args:
        db_type: 数据库类型，可选 mysql、oracle、sqlite、pg。
        query: 额外查询关键词，如 "连接池"、"@Transaction"。
        limit: 返回文档数量上限。
    """
    try:
        if db_type not in {"mysql", "oracle", "sqlite", "pg"}:
            return _err(f"不支持的数据库类型: {db_type}")
        return _ok(_fetch_docs(type_="python", lang=db_type, query=query, limit=limit))
    except Exception as e:
        return _err(f"{e}\n{traceback.format_exc()}")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
