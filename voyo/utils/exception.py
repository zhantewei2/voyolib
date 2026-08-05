from voyo.utils.exception_type import ExceptionType


class VoyoException(Exception):
    """业务异常：code 为 HTTP 风格整数错误码，可直接传 ExceptionType 枚举。"""

    def __init__(self, code: int | ExceptionType, msg: str) -> None:
        self.code = int(code)
        self.msg = msg
        super().__init__(f"[{self.code}] {msg}")

    @classmethod
    def of(cls, exc_type: ExceptionType, msg: str | None = None) -> "VoyoException":
        return cls(exc_type, msg or exc_type.msg)


class YoHttpException(VoyoException):
    """HTTP 请求错误；status_code 为 code 的别名。"""

    @property
    def status_code(self) -> int:
        return self.code


class YoModelException(VoyoException):
    """模型请求错误；status_code 为上游 HTTP 状态码，msg 为上游响应体。"""

    @property
    def status_code(self) -> int:
        return self.code
