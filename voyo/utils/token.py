"""Token 工具 — 基于 tiktoken cl100k_base。"""

import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")


def estimate_token_count(text: str) -> int:
    """估算文本的 token 数。"""
    if not text:
        return 0
    return len(_enc.encode(text))


def encode(text: str) -> list[int]:
    """将文本编码为 token ID 列表。"""
    return _enc.encode(text)


def decode(tokens: list[int]) -> str:
    """将 token ID 列表解码为文本。"""
    return _enc.decode(tokens)


def token_segments(text: str) -> list[tuple[str, int, int]]:
    """返回 [(token_text, start_char, end_char), ...]。"""
    token_ids = _enc.encode(text)
    result = []
    pos = 0
    for tid in token_ids:
        seg = _enc.decode([tid])
        result.append((seg, pos, pos + len(seg)))
        pos += len(seg)
    return result
