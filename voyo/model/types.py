from typing import Any, Literal, NotRequired, TypedDict

# ---------- Anthropic Messages API ----------
# role 仅 user/assistant，system 走顶层 system 参数；工具调用与思维链都是 content 块


class AnthropicTextBlock(TypedDict):
    type: Literal["text"]
    text: str


class AnthropicImageBlock(TypedDict):
    type: Literal["image"]
    # {"type": "base64", "media_type": ..., "data": ...} 或 {"type": "url", "url": ...}
    source: dict[str, Any]


class AnthropicToolUseBlock(TypedDict):
    type: Literal["tool_use"]
    id: str
    name: str
    input: dict[str, Any]


class AnthropicToolResultBlock(TypedDict):
    type: Literal["tool_result"]
    tool_use_id: str
    content: NotRequired[str | list[AnthropicTextBlock | AnthropicImageBlock]]
    is_error: NotRequired[bool]


class AnthropicThinkingBlock(TypedDict):
    type: Literal["thinking"]
    thinking: str
    signature: str


AnthropicContent = str | list[
    AnthropicTextBlock | AnthropicImageBlock | AnthropicToolUseBlock
    | AnthropicToolResultBlock | AnthropicThinkingBlock
]


class AnthropicMsg(TypedDict):
    """Anthropic Messages API 对话消息。"""

    role: Literal["user", "assistant"]
    content: AnthropicContent


# ---------- OpenAI chat/completions ----------
# 工具调用在 assistant.tool_calls，结果以 role:"tool" + tool_call_id 回传


class OpenAiContentText(TypedDict):
    type: Literal["text"]
    text: str


class OpenAiContentImage(TypedDict):
    type: Literal["image_url"]
    # "https://..." 或 {"url": ..., "detail": ...}
    image_url: str | dict[str, Any]


class OpenAiToolCall(TypedDict):
    id: str
    type: Literal["function"]
    # {"name": ..., "arguments": "<json 字符串>"}
    function: dict[str, Any]


OpenAiContent = str | list[OpenAiContentText | OpenAiContentImage]


class OpenAiMsg(TypedDict):
    """OpenAI chat/completions 对话消息。"""

    role: Literal["system", "user", "assistant", "tool"]
    # assistant 可只有 tool_calls 而无 content
    content: NotRequired[OpenAiContent]
    name: NotRequired[str]
    tool_calls: NotRequired[list[OpenAiToolCall]]
    tool_call_id: NotRequired[str]


# ---------- OpenAI Responses API ----------
# input 项：message / function_call / function_call_output / reasoning


class ResponsesInputText(TypedDict):
    type: Literal["input_text"]
    text: str


class ResponsesInputImage(TypedDict):
    type: Literal["input_image"]
    image_url: str


class ResponsesInputVideo(TypedDict):
    type: Literal["input_video"]
    video_url: str


class ResponsesOutputText(TypedDict):
    type: Literal["output_text"]
    text: str


ResponsesContent = str | list[
    ResponsesInputText | ResponsesInputImage | ResponsesInputVideo | ResponsesOutputText
]


class ResponsesMessageItem(TypedDict):
    role: Literal["system", "developer", "user", "assistant"]
    content: ResponsesContent
    type: NotRequired[Literal["message"]]


class ResponsesFunctionCallItem(TypedDict):
    type: Literal["function_call"]
    call_id: str
    name: str
    arguments: str


class ResponsesFunctionCallOutputItem(TypedDict):
    type: Literal["function_call_output"]
    call_id: str
    output: str


class ResponsesReasoningItem(TypedDict):
    type: Literal["reasoning"]
    summary: NotRequired[list[dict[str, Any]]]
    content: NotRequired[list[dict[str, Any]]]


OpenAiResponsesMsg = (
    ResponsesMessageItem | ResponsesFunctionCallItem
    | ResponsesFunctionCallOutputItem | ResponsesReasoningItem
)


class ExtraBody(TypedDict, total=False):
    enable_thinking: bool
    thinking: bool
    preserver_thinking: bool
    reasoning_effort: Literal["high", "max"]


ExtraBodyInput = ExtraBody | dict[str, Any]


class ResponseFormat(TypedDict):
    type: str
