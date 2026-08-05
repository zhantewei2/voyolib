# voyo OpenAiClient — OpenAI 兼容 chat/completions 直连客户端

httpx 直连 OpenAI 兼容 chat/completions API，兼容 Dashscope（通义千问）、OpenAI、DeepSeek、Kimi 等所有 OpenAI 格式服务。支持同步/异步、流式、重试、限流自降级、thinking 开关、token 用量统计。

```python
from voyo.model.openai import OpenAiClient
from voyo.model.base import ModelUsage

client = OpenAiClient(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key="your-api-key",
    headers=None,        # 可选，额外 header，同名字段覆盖默认
    max_workers=0,       # 0 = 不限制并发；>0 时抢信号量控制并发
    rpm=0,               # 0 = 不限速；>0 时按指定 RPM 平滑打请求
)

usage = ModelUsage()   # 调用方 new 实例，传入才统计用量

# 同步调用
raw = client.chat(
    model="qwen-max",
    messages=[{"role": "user", "content": "你好"}],
    system=None,                # system 独立传参，自动前置为 system message
    thinking_enabled=False,     # 默认 False：常驻写入 enable_thinking / chat_template_kwargs / thinking 关闭字段
    temperature=0.0,
    max_tokens=4096,
    extra_body=None,            # 透传合并进 body（如 enable_thinking、reasoning_effort、response_format...）
    retry_max=1,
    stream=False,
    usage=usage,
)
print(raw["choices"][0]["message"]["content"], usage.input_tokens, usage.output_tokens)

# 异步调用
raw = await client.achat(...)

# 流式：返回 SSE 行迭代器（"data: {...}\n"），迭代完毕后 usage 已统计
for line in client.chat(..., stream=True, usage=usage):
    print(line, end="")
```

**说明：**
- `usage`: 传入 `ModelUsage` 实例才统计；属性 `input_tokens` / `output_tokens` / `input_cache_tokens` / `cache_creation_tokens`，可复用实例累计多次调用
- `max_workers` / `rpm`: 默认 0 不启用；>0 时内部 `RateLimiter` 同时控并发 + 平滑打请求节奏；触发限流（429 或 5xx 含 "too many requests"）会自动硬阻塞 30s、降 RPM（步长 5，下限 1），5 分钟未再触发则回升
- 流式不重试（响应已开始输出），非流式按 `retry_max` 重试，每次重试都会重新抢并发信号 + 重新节奏控制
- 错误抛出 `YoModelException`（`status_code` 为上游 HTTP 状态码，`msg` 为上游响应体）