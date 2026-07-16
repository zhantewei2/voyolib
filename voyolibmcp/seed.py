"""导入 mysql / oracle / sqlite / unique_id / logger / methods 文档索引。"""

from __future__ import annotations

import sys

from voyolibmcp.po_docs import DEFAULT_DOCS_DIR, po_docs_db

SEEDS: list[dict[str, str]] = [
    {
        "type": "python",
        "lang": "mysql",
        "question": "mysql 连接池 写sql 事务 @Transaction",
        "doc_name": "mysql",
    },
    {
        "type": "python",
        "lang": "oracle",
        "question": "oracle 连接池 写sql 事务 @transaction",
        "doc_name": "oracle",
    },
    {
        "type": "python",
        "lang": "sqlite",
        "question": "sqlite 数据库文件 写sql 事务 @Transaction",
        "doc_name": "sqlite",
    },
    {
        "type": "tool",
        "lang": "common",
        "question": "unique_id 唯一 ID 分布式 ID",
        "doc_name": "unique_id",
    },
    {
        "type": "tool",
        "lang": "common",
        "question": "logger 日志 init_logger 全局日志",
        "doc_name": "logger",
    },
    {
        "type": "tool",
        "lang": "common",
        "question": "FastAPI fastApi接口响应 返回格式 json gzip",
        "doc_name": "methods",
    },
]


def main() -> None:
    DEFAULT_DOCS_DIR.mkdir(parents=True, exist_ok=True)

    if "--clear" in sys.argv:
        documents = po_docs_db.list().documents
        for doc in documents:
            po_docs_db.delete(id=doc.id)
        print(f"已清理 {len(documents)} 条旧文档")

    for entry in SEEDS:
        doc_path = DEFAULT_DOCS_DIR / f"{entry['doc_name']}.md"
        content = doc_path.read_text(encoding="utf-8")
        result = po_docs_db.write(
            type=entry["type"],
            lang=entry["lang"],
            question=entry["question"],
            doc_name=entry["doc_name"],
            content=content,
        )
        print(f"写入: {entry['doc_name']} (id={result.id})")

    total = len(po_docs_db.list().documents)
    print(f"数据库共 {total} 条文档")
    po_docs_db.close()


if __name__ == "__main__":
    main()
