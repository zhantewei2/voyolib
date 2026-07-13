# voyo logger

全局日志初始化，应用入口调用一次即可。

```python
from voyo.utils import init_logger

init_logger(log_dir="logs", level=logging.INFO)
```

之后使用标准 `logging`：

```python
import logging

logger = logging.getLogger(__name__)
logger.info("hello")
```

日志按时间 + 大小双规则切分，输出到控制台、`logs/info/app.log` 与 `logs/warning/warning.log`。
