from typing import Any

from pydantic import BaseModel

from voyo.utils.json import YOJSONResponse, YoGzipJsonResponses


class Methods:
    @staticmethod
    def resp_result(data: Any, code: int = 200, use_gzip: bool = False):
        if isinstance(data, BaseModel):
            data = data.model_dump()
        elif hasattr(data, "__dict__") and not isinstance(data, dict):
            data = vars(data).copy()
            data.pop("__orig_class__", None)
        content = {"status_code": code, "message": data}
        cls = YoGzipJsonResponses if use_gzip else YOJSONResponse
        return cls(status_code=code, content=content)

    @staticmethod
    def resp_success():
        return {"status_code": 200, "message": "success"}
