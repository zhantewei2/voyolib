"""Integration tests for voyo.model.openai.ModelClient — no mocks."""

from __future__ import annotations

import pytest

from voyo.model.openai import ModelClient

BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
API_KEY = "sk-372b5ed8a6614dd5a3b5ec528f882d26"

@pytest.fixture
def client():
    return ModelClient(base_url=BASE_URL, api_key=API_KEY)


class TestChat:
    def test_basic_call(self, client):
        result = client.chat(model="qwen-max", messages=[{"role": "user", "content": "say hi in 3 words"}])
        content = result.choices[0].message.content
        print(f"\n[basic_call] {content!r}")
        assert isinstance(content, str)
        assert len(content) > 0

    def test_temperature_passed(self, client):
        result = client.chat(model="qwen-max", messages=[{"role": "user", "content": "say hi"}], temperature=0.7)
        content = result.choices[0].message.content
        print(f"\n[temperature] {content!r}")
        assert content

    def test_max_tokens_passed(self, client):
        result = client.chat(model="qwen-max", messages=[{"role": "user", "content": "say hi"}], max_tokens=50)
        content = result.choices[0].message.content
        print(f"\n[max_tokens] {content!r}")
        assert content

    def test_response_format_text(self, client):
        result = client.chat(model="qwen-max", messages=[{"role": "user", "content": "say hi"}], response_format={"type": "text"})
        content = result.choices[0].message.content
        print(f"\n[text_format] {content!r}")
        assert isinstance(content, str)

    def test_response_format_json_object(self, client):
        result = client.chat(
            model="qwen-max",
            messages=[{"role": "user", "content": "return a json with key greeting"}],
            response_format={"type": "json_object"},
        )
        content = result.choices[0].message.content
        print(f"\n[json_object] {content!r}")
        import json
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_extra_body_enable_thinking(self, client):
        result = client.chat(model="qwen-max", messages=[{"role": "user", "content": "1+1=?"}], extra_body={"enable_thinking": True})
        content = result.choices[0].message.content
        print(f"\n[enable_thinking] {content!r}")
        assert content

    def test_extra_body_reasoning_effort(self, client):
        result = client.chat(model="qwen-max", messages=[{"role": "user", "content": "say hi"}], extra_body={"reasoning_effort": "high"})
        content = result.choices[0].message.content
        print(f"\n[reasoning_effort] {content!r}")
        assert content

    def test_stream_returns_iterator(self, client):
        result = client.chat(model="qwen-max", messages=[{"role": "user", "content": "say hi in 5 words"}], stream=True)
        collected = []
        for chunk in result:
            if chunk.choices and chunk.choices[0].delta.content:
                collected.append(chunk.choices[0].delta.content)
        full = "".join(collected)
        print(f"\n[stream] {full!r}")
        assert len(collected) > 0


class TestAchat:
    @pytest.mark.asyncio
    async def test_basic_call(self, client):
        result = await client.achat(model="qwen-max", messages=[{"role": "user", "content": "say hi in 3 words"}])
        content = result.choices[0].message.content
        print(f"\n[achat_basic] {content!r}")
        assert isinstance(content, str)
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_response_format_json_object(self, client):
        result = await client.achat(
            model="qwen-max",
            messages=[{"role": "user", "content": "return a json with key greeting"}],
            response_format={"type": "json_object"},
        )
        content = result.choices[0].message.content
        print(f"\n[achat_json] {content!r}")
        import json
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    @pytest.mark.asyncio
    async def test_stream_async(self, client):
        result = await client.achat(model="qwen-max", messages=[{"role": "user", "content": "say hi in 5 words"}], stream=True)
        collected = []
        async for chunk in result:
            if chunk.choices and chunk.choices[0].delta.content:
                collected.append(chunk.choices[0].delta.content)
        full = "".join(collected)
        print(f"\n[achat_stream] {full!r}")
        assert len(collected) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
