# voyo unique_id

生成分布式唯一数字 ID。

```python
from voyo.utils import yo_unique

uid = yo_unique.get_uid()  # 例如 169123456789012345
```

`get_uid()` 基于毫秒时间戳 + 自增索引 + 随机数，线程安全。
