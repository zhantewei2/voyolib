"""Integration tests for voyo.model.anthropic.AnthropicClient — no mocks."""

from __future__ import annotations

import pytest

from voyo.model.anthropic import AnthropicClient
from voyo.model.base import ModelUsage

BASE_URL = "https://api.longcat.chat/anthropic"
API_KEY = "ak_23v4tG5ol1uH9ik6LR6DB1R13uN7e"
MODEL = "LongCat-2.0"


@pytest.fixture
def client():
    return AnthropicClient(base_url=BASE_URL, api_key=API_KEY)


def _text(raw: dict) -> str:
    return next(b["text"] for b in raw["content"] if b.get("type") == "text")


class TestChat:
    def test_basic_call(self, client):
        raw = client.chat(model=MODEL, messages=[{"role": "user", "content": "say hi in 3 words"}])
        text = _text(raw)
        print(f"\n[basic_call] {text!r}")
        assert isinstance(text, str) and len(text) > 0

    def test_system_and_usage(self, client):
        usage = ModelUsage()
        client.chat(
            model=MODEL,
            messages=[{"role": "user", "content": "hi"}],
            system="reply in one word",
            max_tokens=64,
            usage=usage,
        )
        print(f"\n[usage] {usage}")
        assert usage.input_tokens > 0
        assert usage.output_tokens > 0

    def test_no_usage_param_no_stats(self, client):
        usage = ModelUsage()
        client.chat(model=MODEL, messages=[{"role": "user", "content": "hi"}], max_tokens=16)
        print(f"\n[no_usage] {usage}")
        assert usage.input_tokens == 0 and usage.output_tokens == 0

    def test_thinking_disabled(self, client):
        raw = client.chat(
            model=MODEL,
            messages=[{"role": "user", "content": "say hi"}],
            thinking_enabled=False,
            max_tokens=64,
        )
        types = [b.get("type") for b in raw["content"]]
        print(f"\n[thinking_disabled] block types={types}")
        assert "thinking" not in types
        assert _text(raw)

    def test_stream(self, client):
        usage = ModelUsage()
        lines = list(client.chat(model=MODEL, messages=[{"role": "user", "content": "say hi"}], stream=True, usage=usage))
        print(f"\n[stream] lines={len(lines)} {usage}")
        assert any("content_block_delta" in line for line in lines)
        assert usage.input_tokens > 0 and usage.output_tokens > 0


class TestAChat:
    @pytest.mark.asyncio
    async def test_basic_call(self, client):
        raw = await client.achat(model=MODEL, messages=[{"role": "user", "content": "say hi in 3 words"}])
        text = _text(raw)
        print(f"\n[async basic_call] {text!r}")
        assert isinstance(text, str) and len(text) > 0

    @pytest.mark.asyncio
    async def test_stream(self, client):
        usage = ModelUsage()
        lines = [line async for line in await client.achat(model=MODEL, messages=[{"role": "user", "content": "say hi"}], stream=True, usage=usage)]
        print(f"\n[async stream] lines={len(lines)} {usage}")
        assert any("content_block_delta" in line for line in lines)
        assert usage.input_tokens > 0 and usage.output_tokens > 0
