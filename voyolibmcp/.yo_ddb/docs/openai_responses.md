# voyo OpenAiResponsesClient — OpenAI Responses API 直连客户端

httpx 直连 OpenAI Responses API（/v1/responses），兼容 OpenAI 官方与 MiniMax 等 Responses 格式服务。支持同步/异步、流式、重试、限流自降级、reasoning 推理控制、token 用量统计。

```python
from voyo.model.openai_responses import OpenAiResponsesClient
from voyo.model.base import ModelUsage

client = OpenAiResponsesClient(
    base_url="https://api.minimax.cn/v1",   # 或 https://api.openai.com/v1
    api_key="your-api-key",
    headers=None,        # 可选，额外 header，同名字段覆盖默认
    max_workers=0,       # 0 = 不限制并发；>0 时抢信号量控制并发
    rpm=0,               # 0 = 不限速；>0 时按指定 RPM 平滑打请求
)

usage = ModelUsage()   # 调用方 new 实例，传入才统计用量

# 同步调用
raw = client.chat(
    model="MiniMax-M3.1-Flash",
    messages=[{"role": "user", "content": "你好"}],  # 写入 input，兼容 role/content 数组
    system=None,                # system 独立传参，写入 instructions
    thinking_enabled=False,     # True 时写入 reasoning={"effort": "high"}，可用 extra_body 覆盖档位
    temperature=0.0,            # MiniMax M3.x 不支持 temperature，传入被忽略
    max_tokens=4096,            # 写入 max_output_tokens
    extra_body=None,            # 透传合并进 body（如 {"reasoning": {"effort": "low"}}、{"store": false}）
    retry_max=1,
    stream=False,
    usage=usage,
)
print(raw["output_text"], usage.input_tokens, usage.output_tokens)  # output_text 为响应便捷拼接字段

# 异步调用
raw = await client.achat(...)

# 流式：返回 SSE 行迭代器（"data: {...}\n"），response.completed 事件携带最终 usage
for line in client.chat(..., stream=True, usage=usage):
    print(line, end="")
```

**说明：**
- `usage`: 传入 `ModelUsage` 实例才统计；属性 `input_tokens` / `output_tokens` / `input_cache_tokens`（映射 `input_tokens_details.cached_tokens`）/ `cache_creation_tokens`，可复用实例累计多次调用
- `max_workers` / `rpm`: 默认 0 不启用；>0 时内部 `RateLimiter` 同时控并发 + 平滑打请求节奏；触发限流（429 或 5xx 含 "too many requests"）自动硬阻塞 30s、降 RPM（步长 5，下限 1），5 分钟未再触发则回升
- 流式不重试（响应已开始输出），非流式按 `retry_max` 重试，每次重试都会重新抢并发信号 + 重新节奏控制
- 错误抛出 `YoModelException`（`status_code` 为上游 HTTP 状态码，`msg` 为上游响应体）
- 流式行可用 `voyo.utils.llm_utils.extract_openai_responses_text` 提取 text / thinking_text
