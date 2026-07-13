"""voyolibmcp 工具文档查询冒烟测试。"""

from __future__ import annotations

import json
import sys

from voyolibmcp.server import get_common_tool_doc, get_db_tool_doc


def _load(result: str) -> dict:
    return json.loads(result)


def main() -> int:
    passed = 0
    total = 0

    cases = [
        ("common unique_id", lambda: get_common_tool_doc(tool_name="unique_id")),
        ("common logger", lambda: get_common_tool_doc(tool_name="logger")),
        ("db mysql", lambda: get_db_tool_doc(db_type="mysql", query="连接池")),
        ("db oracle", lambda: get_db_tool_doc(db_type="oracle", query="事务")),
        ("db sqlite", lambda: get_db_tool_doc(db_type="sqlite", query="@Transaction")),
    ]

    for name, call in cases:
        total += 1
        data = _load(call())
        ok = "error" not in data and len(data.get("results", [])) > 0
        ok = ok and any(item.get("content") for item in data.get("results", []))
        if ok:
            passed += 1
        print(f"{'PASS' if ok else 'FAIL'} [{name}] results={len(data.get('results', []))}")
        if not ok:
            print(f"  {data}")

    print(f"\n{passed}/{total} 通过")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
