import logging
import random
from collections.abc import AsyncIterator, Iterator
from typing import Any, Literal, TypedDict

from voyo.model.anthropic import AnthropicClient
from voyo.model.base import ModelUsage
from voyo.model.openai import OpenAiClient
from voyo.model.types import ExtraBodyInput

logger = logging.getLogger(__name__)

ModelType = Literal["anthropic", "openai"]


class HighModelConfig(TypedDict, total=False):
    model_name: str
    model_type: ModelType
    model_url: str
    model_token: str
    model_weight: int
    max_workers: int  # 默认 0 不限制
    rpm: int  # 默认 0 不限制


class _Entry:
    __slots__ = ("client", "model_name", "weight")

    def __init__(self, client: OpenAiClient | AnthropicClient, model_name: str, weight: int) -> None:
        self.client = client
        self.model_name = model_name
        self.weight = weight


class HighModelClient:
    """多供应商 chat 客户端：按 weight 加权随机选择内部 client 发起调用，实现出口端负载均衡。
    max_workers/rpm 在 config 中按模型配置，chat/achat 调用方不传这两个参数。
    """

    def __init__(self, configs: list[HighModelConfig]) -> None:
        if not configs:
            raise ValueError("configs 不能为空")
        self._entries: list[_Entry] = []
        for cfg in configs:
            weight = cfg.get("model_weight", 1)
            if weight <= 0:
                raise ValueError(f"model_weight 必须为正数: {cfg.get('model_name')}")
            model_type: ModelType = cfg.get("model_type", "openai")
            cls = AnthropicClient if model_type == "anthropic" else OpenAiClient
            client = cls(
                base_url=cfg["model_url"],
                api_key=cfg["model_token"],
                max_workers=cfg.get("max_workers", 0),
                rpm=cfg.get("rpm", 0),
            )
            self._entries.append(_Entry(client, cfg["model_name"], weight))
        self._weights = [e.weight for e in self._entries]
        self._random = random.Random()

    def _pick(self) -> _Entry:
        entry = self._random.choices(self._entries, weights=self._weights, k=1)[0]
        logger.info("high_model pick: model=%s", entry.model_name)
        return entry

    def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str | None = None,
        thinking_enabled: bool = False,
        extra_body: ExtraBodyInput | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        retry_max: int = 1,
        stream: bool = False,
        usage: ModelUsage | None = None,
        timeout: float = 300.0,
    ) -> dict[str, Any] | Iterator[str]:
        entry = self._pick()
        return entry.client.chat(
            model=entry.model_name, messages=messages, system=system,
            thinking_enabled=thinking_enabled, extra_body=extra_body,
            temperature=temperature, max_tokens=max_tokens, retry_max=retry_max,
            stream=stream, usage=usage, timeout=timeout,
        )

    async def achat(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str | None = None,
        thinking_enabled: bool = False,
        extra_body: ExtraBodyInput | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        retry_max: int = 1,
        stream: bool = False,
        usage: ModelUsage | None = None,
        timeout: float = 300.0,
    ) -> dict[str, Any] | AsyncIterator[str]:
        entry = self._pick()
        return await entry.client.achat(
            model=entry.model_name, messages=messages, system=system,
            thinking_enabled=thinking_enabled, extra_body=extra_body,
            temperature=temperature, max_tokens=max_tokens, retry_max=retry_max,
            stream=stream, usage=usage, timeout=timeout,
        )
