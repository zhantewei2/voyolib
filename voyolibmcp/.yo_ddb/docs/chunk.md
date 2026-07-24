# voyo chunk_split_paragraph — 按段落/Token 大小切分文本

基于 tiktoken (cl100k_base) 将长文本按 token 大小分块，优先在换行符处切割，支持标点和强制切割兜底。

```python
from voyo.utils.chunk import chunk_split_paragraph

text = "第一段内容。\n第二段内容。\n第三段..."
chunks = chunk_split_paragraph(text, token_size=500, max_tokens=1000)

for item in chunks:
    print(f"token数: {item['token_size']}, 内容: {item['chunk'][:50]}...")
```

**参数说明：**
- `token_size`: 每个 chunk 的目标 token 数
- `max_tokens`: 兜底上限，必须 > token_size；无换行时若前方换行距离超过此值，则找标点 `[.。；;]` 切割，仍无则强制切割
- 返回值：`[{"chunk": str (trimmed), "token_size": int}, ...]`

**切割逻辑：**
1. 按 token_size 预估位置，找最近换行符
2. 后方换行更近 → 切到换行前（缩小）
3. 前方换行更近 → 延伸包含换行（扩大）
4. 无换行 → 前方 max_tokens 内找换行 → 找标点 → 强制切割
5. 下一 chunk 起始自动 left trim，避免空 chunk
