from enum import IntEnum


class ExceptionType(IntEnum):
    """HTTP 风格错误码枚举；msg 属性为默认中文描述。"""

    PARAM_ERROR = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    SERVER_ERROR = 500
    UPSTREAM_ERROR = 502
    TIMEOUT = 504

    @property
    def msg(self) -> str:
        return _MSGS[self]


_MSGS = {
    ExceptionType.PARAM_ERROR: "参数错误",
    ExceptionType.UNAUTHORIZED: "未认证或凭证无效",
    ExceptionType.FORBIDDEN: "无权限",
    ExceptionType.NOT_FOUND: "资源不存在",
    ExceptionType.SERVER_ERROR: "服务器内部错误",
    ExceptionType.UPSTREAM_ERROR: "上游服务错误",
    ExceptionType.TIMEOUT: "请求超时",
}
