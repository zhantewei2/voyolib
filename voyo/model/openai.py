import json
import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx

from voyo.model.base import ModelUsage, build_body
from voyo.model.rate_limit import RateLimiter
from voyo.model.types import ExtraBodyInput
from voyo.utils.exception import YoModelException

logger = logging.getLogger(__name__)

_OK_STATUS = (200, 201, 202)


class OpenAiClient:
    """httpx 直连 OpenAI 兼容 chat/completions API；传入 ModelUsage 实例时才统计 token 用量。
    max_workers 与 rpm 默认 0 表示不限制；>0 时由内部 RateLimiter 控制并发与请求节奏。
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        headers: dict[str, str] | None = None,
        *,
        max_workers: int = 0,
        rpm: int = 0,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
            **(headers or {}),
        }
        self._sync_client = httpx.Client()
        self._async_client = httpx.AsyncClient()
        self._limiter = RateLimiter(rpm=rpm, max_workers=max_workers)

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
        thinking_enabled: bool = False,
        extra_body: ExtraBodyInput | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        retry_max: int = 1,
        stream: bool = False,
        usage: ModelUsage | None = None,
    ) -> dict[str, Any] | Iterator[str]:
        """同步调用；stream=True 返回 SSE 行迭代器，否则返回原始响应 dict。
        非流式：每次重试都重新进入 _limiter.acquire_sync（重新抢 sem + 重新节奏控制）。"""
        call_kwargs = dict(
            model=model, messages=messages, system=system, thinking_enabled=thinking_enabled,
            extra_body=extra_body, temperature=temperature, max_tokens=max_tokens,
            stream=stream, usage=usage,
        )
        if stream:
            # 流式不能重试（响应已开始流式输出）
            with self._limiter.acquire_sync():
                return self._chat(**call_kwargs)
        for _req_count in range(retry_max):
            try:
                with self._limiter.acquire_sync():
                    return self._chat(**call_kwargs)
            except YoModelException as err:
                logger.error(
                    "openai request failed: status=%s body=%s", err.status_code, err.msg,
                )
                self._limiter.is_rate_limited_text(err.status_code, err.msg)
                if _req_count == retry_max - 1:
                    raise err
                continue

    async def achat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
        thinking_enabled: bool = False,
        extra_body: ExtraBodyInput | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        retry_max: int = 1,
        stream: bool = False,
        usage: ModelUsage | None = None,
    ) -> dict[str, Any] | AsyncIterator[str]:
        """异步调用；stream=True 返回 SSE 行异步迭代器，否则返回原始响应 dict。
        非流式：每次重试都重新进入 _limiter.acquire（重新抢 asem + 重新节奏控制）。"""
        call_kwargs = dict(
            model=model, messages=messages, system=system, thinking_enabled=thinking_enabled,
            extra_body=extra_body, temperature=temperature, max_tokens=max_tokens,
            stream=stream, usage=usage,
        )
        if stream:
            async with self._limiter.acquire():
                return await self._achat(**call_kwargs)
        for _req_count in range(retry_max):
            try:
                async with self._limiter.acquire():
                    return await self._achat(**call_kwargs)
            except YoModelException as err:
                logger.error(
                    "openai request failed: status=%s body=%s", err.status_code, err.msg,
                )
                self._limiter.is_rate_limited_text(err.status_code, err.msg)
                if _req_count == retry_max - 1:
                    raise err
                continue

    def _chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
        thinking_enabled: bool = False,
        extra_body: ExtraBodyInput | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        stream: bool = False,
        usage: ModelUsage | None = None,
    ) -> dict[str, Any] | Iterator[str]:
        """单次实际同步请求（不含并发/限速/重试）。"""
        body = self._make_body(
            model=model, messages=messages, system=system, thinking_enabled=thinking_enabled,
            temperature=temperature, max_tokens=max_tokens, extra_body=extra_body, stream=stream,
        )
        if stream:
            return self._stream_sync(body, usage)
        resp = self._sync_client.post(self._url, json=body, headers=self._headers, timeout=300.0)
        if resp.status_code not in _OK_STATUS:
            raise YoModelException(resp.status_code, resp.text)
        raw = resp.json()
        self._collect_usage(usage, raw.get("usage"))
        return raw

    async def _achat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
        thinking_enabled: bool = False,
        extra_body: ExtraBodyInput | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        stream: bool = False,
        usage: ModelUsage | None = None,
    ) -> dict[str, Any] | AsyncIterator[str]:
        """单次实际异步请求（不含并发/限速/重试）。"""
        body = self._make_body(
            model=model, messages=messages, system=system, thinking_enabled=thinking_enabled,
            temperature=temperature, max_tokens=max_tokens, extra_body=extra_body, stream=stream,
        )
        if stream:
            return self._stream_async(body, usage)
        resp = await self._async_client.post(self._url, json=body, headers=self._headers, timeout=300.0)
        if resp.status_code not in _OK_STATUS:
            raise YoModelException(resp.status_code, resp.text)
        raw = resp.json()
        self._collect_usage(usage, raw.get("usage"))
        return raw

    @staticmethod
    def _make_body(
        *, model: str, messages: list[dict[str, Any]], system: str | None,
        thinking_enabled: bool, temperature: float, max_tokens: int,
        extra_body: ExtraBodyInput | None, stream: bool,
    ) -> dict[str, Any]:
        if system:
            messages = [{"role": "system", "content": system}, *messages]
        body = build_body(
            model=model, messages=messages, system=None, thinking_enabled=thinking_enabled,
            temperature=temperature, max_tokens=max_tokens, extra_body=extra_body, stream=stream,
        )
        if stream:
            body["stream_options"] = {"include_usage": True}
        return body

    def _stream_sync(self, body: dict[str, Any], usage: ModelUsage | None) -> Iterator[str]:
        stream_usage: dict[str, Any] = {}
        with self._sync_client.stream("POST", self._url, json=body, headers=self._headers, timeout=120.0) as resp:
            if resp.status_code not in _OK_STATUS:
                resp.read()
                raise YoModelException(resp.status_code, resp.text)
            for line in resp.iter_lines():
                if not line:
                    continue
                event = self._parse_event(line)
                if event and event.get("usage"):
                    stream_usage = event["usage"]
                yield f"{line}\n"
        self._collect_usage(usage, stream_usage)

    async def _stream_async(self, body: dict[str, Any], usage: ModelUsage | None) -> AsyncIterator[str]:
        stream_usage: dict[str, Any] = {}
        async with self._async_client.stream("POST", self._url, json=body, headers=self._headers, timeout=120.0) as resp:
            if resp.status_code not in _OK_STATUS:
                await resp.aread()
                raise YoModelException(resp.status_code, resp.text)
            async for line in resp.aiter_lines():
                if not line:
                    continue
                event = self._parse_event(line)
                if event and event.get("usage"):
                    stream_usage = event["usage"]
                yield f"{line}\n"
        self._collect_usage(usage, stream_usage)

    @staticmethod
    def _collect_usage(usage: ModelUsage | None, raw_usage: dict[str, Any] | None) -> None:
        if usage is None:
            return
        # OpenAI 字段名映射为 anthropic 风格后再累加
        mapped = {
            "input_tokens": (raw_usage or {}).get("prompt_tokens", 0),
            "output_tokens": (raw_usage or {}).get("completion_tokens", 0),
        }
        usage.add(mapped)
        logger.info("usage: input_tokens=%s output_tokens=%s", usage.input_tokens, usage.output_tokens)

    @staticmethod
    def _parse_event(line: str) -> dict[str, Any] | None:
        if not line.startswith("data:"):
            return None
        data = line[5:].strip()
        if data == "[DONE]":
            return None
        try:
            return json.loads(data)
        except ValueError:
            return None
