# -*- coding: utf-8 -*-
"""
HTTP 异常类定义
遵循 HTTP 状态码语义，供路由匹配、视图函数、中间件统一抛出。
"""


class HTTPException(Exception):
    """HTTP 异常基类"""
    status_code = 500
    default_message = "Internal Server Error"

    def __init__(self, message=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        self.message = message or self.default_message
        super().__init__(self.message)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.status_code} {self.message}>"


class BadRequest(HTTPException):
    """400 Bad Request"""
    status_code = 400
    default_message = "Bad Request"


class Unauthorized(HTTPException):
    """401 Unauthorized"""
    status_code = 401
    default_message = "Unauthorized"


class Forbidden(HTTPException):
    """403 Forbidden"""
    status_code = 403
    default_message = "Forbidden"


class NotFound(HTTPException):
    """404 Not Found"""
    status_code = 404
    default_message = "Not Found"


class MethodNotAllowed(HTTPException):
    """405 Method Not Allowed"""
    status_code = 405
    default_message = "Method Not Allowed"


class InternalServerError(HTTPException):
    """500 Internal Server Error"""
    status_code = 500
    default_message = "Internal Server Error"


# 状态码 → 标准原因短语映射（用于 WSGI start_response）
STATUS_PHRASES = {
    200: "OK",
    201: "Created",
    202: "Accepted",
    204: "No Content",
    301: "Moved Permanently",
    302: "Found",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
}
