from pydantic import BaseModel

from vooyo.utils.json import YOJSONResponse,YoGzipJsonResponses
from typing import Any

class Methods():

    @staticmethod
    def resp_result(data:Any, code:int=200, use_gzip:bool=False):
        if isinstance(data,BaseModel):
            data=data.model_dump()
        elif hasattr(data,"__dict__") and not isinstance(data,dict):
            data=vars(data).copy()
            data.pop("__orig_class__", None)
        if not use_gzip:
            return YOJSONResponse(
                status_code=code,
                content={
                    "status_code": code,
                    "message": data
                }
            )
        else:
            return YoGzipJsonResponses(
                status_code=code,
                content={
                    "status_code": code,
                    "message": data
                }
            )

    