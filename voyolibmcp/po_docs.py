"""voyolibmcp PoDocsDB 客户端：单线程工作者，保证 sqlite 连接只在一个线程创建与使用。"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from po_docs_db import PoDocsDB

ROOT = Path(__file__).resolve().parent

# 路径相对于本文件地址解析，不硬编码 /Users/momo
DEFAULT_DB_PATH = (ROOT / ".yo_ddb" / "data" / "docs.db").resolve()
DEFAULT_DOCS_DIR = (ROOT / ".yo_ddb" / "docs").resolve()


class PoDocsWorker:
    """固定单线程 executor 持有 PoDocsDB：mcp 2.x 的工具在任意 worker 线程执行，
    而 sqlite 连接有线程亲和性，必须让连接始终在同一个线程创建与使用。"""

    def __init__(self, db_path: str, docs_dir: str) -> None:
        self._db_path = db_path
        self._docs_dir = docs_dir
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="po-docs")
        self._db: PoDocsDB | None = None

    def _get_db(self) -> PoDocsDB:
        # 仅在 worker 线程内调用，连接惰性创建于该线程
        if self._db is None:
            self._db = PoDocsDB(db_path=self._db_path, docs_dir=self._docs_dir)
        return self._db

    async def run(self, fn: Callable[[PoDocsDB], Any]) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, lambda: fn(self._get_db()))


po_docs_worker = PoDocsWorker(db_path=str(DEFAULT_DB_PATH), docs_dir=str(DEFAULT_DOCS_DIR))


def read_doc(doc_path: str) -> str:
    """根据数据库中存储的相对路径读取文档内容。"""
    full_path = DEFAULT_DOCS_DIR / doc_path
    if not full_path.exists():
        return ""
    return full_path.read_text(encoding="utf-8")
