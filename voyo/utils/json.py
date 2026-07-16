
import json
from datetime import datetime
from typing import Any,Dict,Union
from pydantic import BaseModel
from fastapi.responses import JSONResponse,Response
import gzip

class CustomEncoder(json.JSONEncoder):
    def encode(self,obj):
        obj=self.convert(obj)
        return super().encode(obj)

    def convert(self, obj):
        if isinstance(obj,int):
            if abs(obj) > 2**53 - 1:
                return str(obj)
            return obj
        elif isinstance(obj,datetime):
            return obj.strftime("%Y/%m/%d %H:%M:%S")
        elif isinstance(obj,BaseModel):
            return self.convert(obj.model_dump())
        elif isinstance(obj,dict):
            return {k: self.convert(v) for k, v in obj.items()}
        elif isinstance(obj,list):
            return [self.convert(item) for item in obj]
        else:
            return obj


class JSON:

    @staticmethod
    def parse(content:str):
        return json.loads(content)
    @staticmethod
    def json(obj:dict|list,indent:int=None)->str:
        r= json.dumps(obj,cls=CustomEncoder,ensure_ascii=False,indent=indent)
        return r

class YOJSONResponse(JSONResponse):
    def render(self, content)->bytes:
        body= JSON.json(content).encode("utf-8")
        return  body

class YoGzipJsonResponses(Response):
    def __init__(self, content:Any, **kwargs):
        body = JSON.json(content).encode("utf-8") if not isinstance(content,str) else content.encode("utf-8")
        body=gzip.compress(body)
        super().__init__(
            content=body,
            headers={
                "Content-type": "application/json; charset=utf-8",
                "Content-Encoding": "gzip"
            }
        )
