# voyo AnthropicClient — Anthropic Messages API 直连客户端

httpx 直连 Anthropic Messages API（不依赖官方 SDK），兼容官方及各类 Anthropic 格式网关（如 longcat）。支持同步/异步、流式、重试、thinking 开关、token 用量统计。

```python
from voyo.model.anthropic import AnthropicClient
from voyo.model.base import ModelUsage

client = AnthropicClient(
    base_url="https://api.anthropic.com",   # 或网关地址，带不带 /v1 均可
    api_key="your-api-key",                 # 自动同时发送 x-api-key 和 Authorization: Bearer
    headers={"anthropic-beta": "..."},      # 可选，额外 header，同名字段覆盖默认
)

usage = ModelUsage()   # 调用方 new 实例，传入才统计用量

# 同步调用
raw = client.chat(
    model="claude-sonnet-5",
    messages=[{"role": "user", "content": "你好"}],
    system="你是助手",              # system 独立传参
    thinking_enabled=False,          # 默认 False：常驻写入 enable_thinking / chat_template_kwargs / thinking 关闭字段
    temperature=0.0,
    max_tokens=4096,
    extra_body=None,                 # 透传合并进 body
    retry_max=1,
    stream=False,
    usage=usage,
)
text = next(b["text"] for b in raw["content"] if b.get("type") == "text")
print(usage.input_tokens, usage.output_tokens)

# 异步调用
raw = await client.achat(...)

# 流式：返回 SSE 行迭代器，迭代完毕后 usage 已统计
for line in client.chat(..., stream=True, usage=usage):
    print(line, end="")
```

**说明：**
- `usage`: 传入 `ModelUsage` 实例才统计；属性 `input_tokens` / `output_tokens` / `input_cache_tokens` / `cache_creation_tokens`，可复用实例累计多次调用
- 非流式响应为原始 dict，文本取 `content` 中 `type == "text"` 的 block（thinking 模型可能含 `thinking` block）
- 错误抛出 `AnthropicError`（带 `status_code`）；非流式按 `retry_max` 重试，流式单次尝试
- 网关差异：认证同时发 `x-api-key` 与 `Authorization: Bearer`；流式 usage 兼容 `message_start` / `message_delta` 两种位置
