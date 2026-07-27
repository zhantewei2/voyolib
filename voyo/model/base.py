from typing import Any

from voyo.model.types import ExtraBodyInput


class ModelUsage:
    """单次/多次调用的 token 用量，由调用方 new 实例传入，调用后读取。"""

    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.input_cache_tokens = 0
        self.cache_creation_tokens = 0

    def add(self, usage: dict[str, Any] | None) -> None:
        if not usage:
            return
        self.input_tokens += usage.get("input_tokens", 0)
        self.output_tokens += usage.get("output_tokens", 0)
        self.input_cache_tokens += usage.get("cache_read_input_tokens", 0)
        self.cache_creation_tokens += usage.get("cache_creation_input_tokens", 0)

    def __repr__(self) -> str:
        return (
            f"ModelUsage(input={self.input_tokens}, output={self.output_tokens}, "
            f"cache_read={self.input_cache_tokens}, cache_creation={self.cache_creation_tokens})"
        )


def build_body(
    *,
    model: str,
    messages: list[dict[str, Any]],
    system: str | None,
    thinking_enabled: bool,
    temperature: float,
    max_tokens: int,
    extra_body: ExtraBodyInput | None,
    stream: bool,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }
    if system:
        body["system"] = system
    if extra_body:
        body.update(extra_body)
    # 关闭 thinking 的字段常驻，网关只认其中一种写法，全部写上
    enabled = thinking_enabled is True
    body["enable_thinking"] = enabled
    kwargs = dict(body.get("chat_template_kwargs") or {})
    kwargs["enable_thinking"] = enabled
    body["chat_template_kwargs"] = kwargs
    if not enabled:
        body["thinking"] = {"type": "disabled"}
    return body
