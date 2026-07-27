# voyo Methods

FastAPI 接口统一响应工具。

```python
from voyo.utils import Methods

# 返回 {"status_code": 200, "message": data}
# data 支持 dict / pydantic 模型 / 普通对象
return Methods.resp_result({"name": "tom"})

# 指定状态码，use_gzip=True 时 gzip 压缩响应体
return Methods.resp_result(data, code=201, use_gzip=True)

# 直接返回成功 {"status_code": 200, "message": "success"}
return Methods.resp_success()
```
