"""LLM 流式行解析工具 — 从各协议 SSE 原始行中提取 text 与 thinking_text，与客户端逻辑解耦。"""
from typing import TypedDict

from voyo.model.anthropic import AnthropicClient
from voyo.model.openai import OpenAiClient
from voyo.model.openai_responses import OpenAiResponsesClient


class Extract_Llm_Stream(TypedDict):
    text: str
    thinking_text: str


def extract_openai_text(row_text: str) -> Extract_Llm_Stream | None:
    """chat/completions 流式行 → text / thinking_text。"""
    row_data = OpenAiClient._parse_event(row_text)
    if not row_data:
        return None
    choices = row_data.get("choices") or []
    if not choices:
        return None
    delta = choices[0].get("delta") or {}
    text = delta.get("content")
    thinking_text = delta.get("reasoning_content") or delta.get("reasoning")
    return {"text": text or "", "thinking_text": thinking_text or ""}


def extract_openai_responses_text(row_text: str) -> Extract_Llm_Stream | None:
    """Responses API 流式行 → text / thinking_text。"""
    event = OpenAiResponsesClient._parse_event(row_text)
    if not event:
        return None
    etype = event.get("type") or ""
    if etype == "response.output_text.delta":
        return {"text": event.get("delta") or "", "thinking_text": ""}
    # reasoning_text: MiniMax；reasoning_summary_text: OpenAI 官方
    if etype in ("response.reasoning_text.delta", "response.reasoning_summary_text.delta"):
        return {"text": "", "thinking_text": event.get("delta") or ""}
    return None


def extract_anthropic_text(row_text: str) -> Extract_Llm_Stream | None:
    """Anthropic Messages 流式行 → text / thinking_text。"""
    event = AnthropicClient._parse_event(row_text)
    if not event:
        return None
    if event.get("type") != "content_block_delta":
        return None
    delta = event.get("delta") or {}
    dtype = delta.get("type")
    if dtype == "text_delta":
        return {"text": delta.get("text") or "", "thinking_text": ""}
    if dtype == "thinking_delta":
        return {"text": "", "thinking_text": delta.get("thinking") or ""}
    return None
