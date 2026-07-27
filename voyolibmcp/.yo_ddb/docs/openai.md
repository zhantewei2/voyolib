# voyo ModelClient — 大模型对话接口调用

通过 OpenAI SDK 规范调用大模型 Chat 接口，兼容 Dashscope（通义千问）、OpenAI、DeepSeek、Kimi 等所有 OpenAI 格式服务。支持同步/异步、流式、重试、思考模式。

```python
from voyo.model.openai import ModelClient

client = ModelClient(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key="your-api-key",
)

# 同步调用
result = client.chat(
    model="qwen-max",
    messages=[{"role": "user", "content": "你好"}],
    temperature=0.7,
    max_tokens=1024,
    response_format={"type": "text"},
    extra_body={"enable_thinking": True, "reasoning_effort": "high"},
    retry_max=2,
    stream=False,
)
print(result.choices[0].message.content)

# 异步调用
result = await client.achat(...)

# 流式
for chunk in client.chat(..., stream=True):
    print(chunk.choices[0].delta.content or "", end="")
```

**参数说明：**
- `extra_body`: 透传给 API，支持 `enable_thinking`、`thinking`、`preserver_thinking`、`reasoning_effort`（"high"/"max"）等
- `retry_max`: 最大尝试次数（默认 1），耗尽后抛出最后一次异常
- `stream`: True 返回迭代器，False 返回完整响应
