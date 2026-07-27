"""Integration tests for voyo.model.openai.ModelClient (httpx 直连重构版) — no mocks."""

from __future__ import annotations

import pytest

from voyo.model.base import ModelUsage, build_body
from voyo.model.openai import ModelClient

BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
API_KEY = "sk-372b5ed8a6614dd5a3b5ec528f882d26"
MODEL = "qwen-max"
THINKING_MODEL = "qwen3-max"


@pytest.fixture
def client():
    return ModelClient(base_url=BASE_URL, api_key=API_KEY)


def _content(raw: dict) -> str:
    return raw["choices"][0]["message"]["content"]


class TestChat:
    def test_basic_call(self, client):
        raw = client.chat(model=MODEL, messages=[{"role": "user", "content": "say hi in 3 words"}])
        content = _content(raw)
        print(f"\n[basic_call] {content!r}")
        assert isinstance(content, str) and len(content) > 0

    def test_base_url_trailing_slash(self):
        client = ModelClient(base_url=BASE_URL + "/", api_key=API_KEY)
        raw = client.chat(model=MODEL, messages=[{"role": "user", "content": "hi"}], max_tokens=16)
        print(f"\n[trailing_slash] {_content(raw)!r}")
        assert _content(raw)

    def test_system_param(self, client):
        raw = client.chat(
            model=MODEL,
            messages=[{"role": "user", "content": "ping"}],
            system="回复只准输出一个词: PONG",
            max_tokens=32,
        )
        content = _content(raw)
        print(f"\n[system] {content!r}")
        assert "PONG" in content.upper()

    def test_usage_non_stream(self, client):
        usage = ModelUsage()
        raw = client.chat(model=MODEL, messages=[{"role": "user", "content": "hi"}], usage=usage)
        print(f"\n[usage] raw={raw.get('usage')} {usage}")
        assert usage.input_tokens > 0 and usage.output_tokens > 0
        # prompt_tokens/completion_tokens 必须映射到 input_tokens/output_tokens
        assert usage.input_tokens == raw["usage"]["prompt_tokens"]
        assert usage.output_tokens == raw["usage"]["completion_tokens"]

    def test_no_usage_param_no_stats(self, client):
        usage = ModelUsage()
        client.chat(model=MODEL, messages=[{"role": "user", "content": "hi"}], max_tokens=16)
        print(f"\n[no_usage] {usage}")
        assert usage.input_tokens == 0 and usage.output_tokens == 0

    def test_thinking_enabled(self, client):
        raw = client.chat(
            model=THINKING_MODEL,
            messages=[{"role": "user", "content": "1+1=?"}],
            thinking_enabled=True,
            max_tokens=2048,
        )
        reasoning = raw["choices"][0]["message"].get("reasoning_content")
        print(f"\n[thinking_enabled] reasoning={str(reasoning)[:120]!r}")
        assert reasoning

    def test_thinking_body_fields(self):
        body = build_body(
            model=MODEL, messages=[{"role": "user", "content": "hi"}], system=None,
            thinking_enabled=False, temperature=0.0, max_tokens=64, extra_body=None, stream=False,
        )
        print(f"\n[thinking_body off] enable_thinking={body['enable_thinking']} kwargs={body['chat_template_kwargs']} thinking={body.get('thinking')}")
        # 关闭 thinking 的字段常驻，网关只认其中一种写法，全部写上
        assert body["enable_thinking"] is False
        assert body["chat_template_kwargs"]["enable_thinking"] is False
        assert body["thinking"] == {"type": "disabled"}

        body_on = build_body(
            model=MODEL, messages=[{"role": "user", "content": "hi"}], system=None,
            thinking_enabled=True, temperature=0.0, max_tokens=64, extra_body=None, stream=False,
        )
        print(f"[thinking_body on] enable_thinking={body_on['enable_thinking']} kwargs={body_on['chat_template_kwargs']} thinking={body_on.get('thinking')}")
        assert body_on["enable_thinking"] is True
        assert body_on["chat_template_kwargs"]["enable_thinking"] is True
        assert "thinking" not in body_on

    def test_stream_returns_sse_lines(self, client):
        lines = list(client.chat(model=MODEL, messages=[{"role": "user", "content": "say hi"}], stream=True))
        data_lines = [line for line in lines if line.startswith("data:")]
        print(f"\n[stream] lines={len(lines)} data_lines={len(data_lines)} first={data_lines[0][:100]!r}")
        assert data_lines
        assert any("chat.completion.chunk" in line for line in data_lines)

    def test_stream_usage(self, client):
        usage = ModelUsage()
        lines = list(client.chat(model=MODEL, messages=[{"role": "user", "content": "hi"}], stream=True, usage=usage))
        print(f"\n[stream_usage] lines={len(lines)} {usage}")
        assert usage.input_tokens > 0 and usage.output_tokens > 0

    def test_error_bad_api_key(self):
        client = ModelClient(base_url=BASE_URL, api_key="sk-wrong")
        with pytest.raises(Exception) as exc_info:
            client.chat(model=MODEL, messages=[{"role": "user", "content": "hi"}], retry_max=2)
        print(f"\n[bad_key] {exc_info.type.__name__}: {str(exc_info.value)[:120]}")

    def test_headers_merge_extra_header(self):
        client = ModelClient(base_url=BASE_URL, api_key=API_KEY, headers={"X-Custom-Header": "voyo-test"})
        raw = client.chat(model=MODEL, messages=[{"role": "user", "content": "hi"}], max_tokens=16)
        print(f"\n[headers_merge] {_content(raw)!r}")
        assert _content(raw)

    def test_headers_merge_override_auth(self):
        # 自定义 header 覆盖默认 Authorization 后请求应 401
        client = ModelClient(base_url=BASE_URL, api_key=API_KEY, headers={"Authorization": "Bearer sk-wrong"})
        with pytest.raises(Exception) as exc_info:
            client.chat(model=MODEL, messages=[{"role": "user", "content": "hi"}])
        print(f"\n[headers_override] {exc_info.type.__name__}: {str(exc_info.value)[:120]}")


class TestAChat:
    @pytest.mark.asyncio
    async def test_basic_call(self, client):
        raw = await client.achat(model=MODEL, messages=[{"role": "user", "content": "say hi in 3 words"}])
        content = _content(raw)
        print(f"\n[async basic_call] {content!r}")
        assert isinstance(content, str) and len(content) > 0

    @pytest.mark.asyncio
    async def test_stream(self, client):
        usage = ModelUsage()
        lines = [line async for line in await client.achat(model=MODEL, messages=[{"role": "user", "content": "say hi"}], stream=True, usage=usage)]
        data_lines = [line for line in lines if line.startswith("data:")]
        print(f"\n[async stream] lines={len(lines)} data_lines={len(data_lines)} {usage}")
        assert data_lines
        assert usage.input_tokens > 0 and usage.output_tokens > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
