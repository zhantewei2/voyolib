"""Tests for voyo.utils.token and voyo.utils.chunk — 基于 tiktoken。"""

from __future__ import annotations

import pytest

from voyo.utils.token import estimate_token_count
from voyo.utils.chunk import chunk_split_paragraph


# ---------------------------------------------------------------------------
# estimate_token_count（基于 tiktoken cl100k_base）
# ---------------------------------------------------------------------------


class TestEstimateTokenCount:
    def test_empty_string_returns_zero(self):
        assert estimate_token_count("") == 0

    def test_pure_chinese(self):
        # tiktoken 对中文的编码结果
        assert estimate_token_count("你好") > 0
        assert estimate_token_count("你好世界") > estimate_token_count("你好")

    def test_pure_english(self):
        assert estimate_token_count("hello") > 0
        assert estimate_token_count("abcd") > 0
        assert estimate_token_count("a") > 0

    def test_mixed_chinese_english(self):
        assert estimate_token_count("你好world") > 0
        assert estimate_token_count("测试ab") > 0

    def test_spaces_and_punctuation(self):
        assert estimate_token_count(" ") > 0
        assert estimate_token_count("，") > 0


# ---------------------------------------------------------------------------
# chunk_split_paragraph
# ---------------------------------------------------------------------------


class TestChunkSplitParagraph:
    def test_short_text_returns_single_chunk(self):
        """短文本（< token_size）应返回 1 个 chunk。"""
        text = "这是一个短文本。"
        result = chunk_split_paragraph(text, token_size=100, max_tokens=200)
        print(f"\n[short] chunks={len(result)}, data={result}")
        assert len(result) == 1
        assert result[0]["chunk"] == text
        assert result[0]["token_size"] == estimate_token_count(text)

    def test_empty_string_returns_empty_list(self):
        result = chunk_split_paragraph("", token_size=10, max_tokens=20)
        assert result == []

    def test_split_by_newline(self):
        """按换行符正常分割。"""
        text = "第一行内容。\n第二行内容。\n第三行内容。"
        result = chunk_split_paragraph(text, token_size=4, max_tokens=10)
        print(f"\n[newline] chunks={len(result)}")
        for i, c in enumerate(result):
            print(f"  [{i}] token_size={c['token_size']}, chunk={c['chunk']!r}")
        assert len(result) >= 2
        for c in result:
            assert c["chunk"] == c["chunk"].strip()
        for c in result:
            assert len(c["chunk"]) > 0

    def test_fallback_to_max_tokens_when_no_newline(self):
        """无换行符时按 max_tokens 兜底切割。"""
        text = "abcdefghij" * 50  # 500 chars
        token_size = 5
        max_tokens = 10
        result = chunk_split_paragraph(text, token_size=token_size, max_tokens=max_tokens)
        print(f"\n[fallback] chunks={len(result)}")
        for i, c in enumerate(result[:5]):
            print(f"  [{i}] token_size={c['token_size']}, len={len(c['chunk'])}")
        assert len(result) >= 2

    def test_split_by_punctuation_when_newline_too_far(self):
        """有句号/分号等标点时按标点切割。"""
        part1 = "a" * 30 + "。"
        part2 = "b" * 30 + "；"
        part3 = "c" * 30
        text = part1 + part2 + part3
        result = chunk_split_paragraph(text, token_size=2, max_tokens=20)
        print(f"\n[punct] chunks={len(result)}")
        for i, c in enumerate(result):
            print(f"  [{i}] token_size={c['token_size']}, chunk={c['chunk']!r}")
        assert len(result) >= 2

    def test_return_format(self):
        """验证返回格式 {"chunk": str, "token_size": int}。"""
        text = "第一行。\n第二行。"
        result = chunk_split_paragraph(text, token_size=4, max_tokens=10)
        for c in result:
            assert isinstance(c, dict)
            assert "chunk" in c
            assert "token_size" in c
            assert isinstance(c["chunk"], str)
            assert isinstance(c["token_size"], int)

    def test_no_leading_trailing_whitespace(self):
        """验证 chunk 无首尾空白。"""
        text = "  \n  hello world  \n  foo bar  \n  "
        result = chunk_split_paragraph(text, token_size=4, max_tokens=10)
        print(f"\n[trim] chunks={len(result)}")
        for i, c in enumerate(result):
            print(f"  [{i}] chunk={c['chunk']!r}")
            assert c["chunk"] == c["chunk"].strip()
            assert len(c["chunk"]) > 0

    def test_no_empty_chunks(self):
        """验证无空 chunk。"""
        text = "aaa\n\n\nbbb\n\nccc"
        result = chunk_split_paragraph(text, token_size=2, max_tokens=10)
        print(f"\n[no_empty] chunks={len(result)}")
        for i, c in enumerate(result):
            print(f"  [{i}] chunk={c['chunk']!r}")
            assert len(c["chunk"]) > 0

    def test_reconstruct_original_text(self):
        """验证所有 chunk 拼接后能还原原文（忽略空白差异）。"""
        text = "第一行内容。\n第二行内容更长一些。\n第三行。\n第四行内容在这里。"
        result = chunk_split_paragraph(text, token_size=4, max_tokens=10)
        print(f"\n[reconstruct] chunks={len(result)}")
        for i, c in enumerate(result):
            print(f"  [{i}] chunk={c['chunk']!r}")
        joined = "".join(c["chunk"] for c in result)
        assert joined.replace(" ", "").replace("\n", "") == text.replace(" ", "").replace("\n", "")

    def test_chinese_text_chunking(self):
        """测试中文文本分块。"""
        text = "一二三四五六七八九十"
        result = chunk_split_paragraph(text, token_size=4, max_tokens=10)
        print(f"\n[chinese] chunks={len(result)}")
        for i, c in enumerate(result):
            print(f"  [{i}] token_size={c['token_size']}, chunk={c['chunk']!r}")
        assert len(result) >= 1
        for c in result:
            assert c["token_size"] == estimate_token_count(c["chunk"])

    def test_token_size_matches_estimate(self):
        """验证每个 chunk 的 token_size 与 estimate_token_count 一致。"""
        text = "hello world 你好世界 foo bar baz 测试文本"
        result = chunk_split_paragraph(text, token_size=8, max_tokens=20)
        for c in result:
            assert c["token_size"] == estimate_token_count(c["chunk"])
