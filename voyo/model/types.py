from typing import Any, Literal, TypedDict


class ExtraBody(TypedDict, total=False):
    enable_thinking: bool
    thinking: bool
    preserver_thinking: bool
    reasoning_effort: Literal["high", "max"]


ExtraBodyInput = ExtraBody | dict[str, Any]


class ResponseFormat(TypedDict):
    type: str
