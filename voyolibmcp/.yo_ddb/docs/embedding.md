# voyo EmbeddingClient — 文本向量嵌入

通过 OpenAI 兼容接口获取文本向量，支持单条/批量、同步/异步。

```python
from voyo.model.embedding import EmbeddingClient

client = EmbeddingClient(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key="your-api-key",
)

# 单条嵌入
vec: list[float] = client.embed(model="text-embedding-v4", input="Hello world")

# 批量嵌入
vectors: list[list[float]] = client.embed_batch(
    model="text-embedding-v4",
    input=["文本一", "文本二", "文本三"],
)

# 异步
vec = await client.aembed(model="text-embedding-v4", input="Hello")
vectors = await client.aembed_batch(model="text-embedding-v4", input=["a", "b"])
```

**参数说明：**
- `model`: 模型名，如 `text-embedding-v4`（返回 1024 维向量）
- `retry_max`: 最大尝试次数（默认 2）
- `input`: 单条为 str，批量为 list[str]
