"""voyolibmcp PoDocsDB 客户端：集中管理 db_path、docs_dir 与单例。"""

from __future__ import annotations

from pathlib import Path

from po_docs_db import PoDocsDB

ROOT = Path(__file__).resolve().parent

# 路径相对于本文件地址解析，不硬编码 /Users/momo
DEFAULT_DB_PATH = (ROOT / ".yo_ddb" / "data" / "docs.db").resolve()
DEFAULT_DOCS_DIR = (ROOT / ".yo_ddb" / "docs").resolve()

po_docs_db = PoDocsDB(db_path=str(DEFAULT_DB_PATH), docs_dir=str(DEFAULT_DOCS_DIR))


def read_doc(doc_path: str) -> str:
    """根据数据库中存储的相对路径读取文档内容。"""
    full_path = DEFAULT_DOCS_DIR / doc_path
    if not full_path.exists():
        return ""
    return full_path.read_text(encoding="utf-8")
