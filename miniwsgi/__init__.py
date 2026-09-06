# -*- coding: utf-8 -*-
"""
MiniWSGI — 遵循 PEP 3333 的轻量级 WSGI Web 框架。
零第三方依赖，仅使用 Python 标准库。

快速开始：
    from miniwsgi import MiniWSGI, Response

    app = MiniWSGI()

    @app.route("/")
    def index(request):
        return {"message": "Hello, MiniWSGI!"}

    app.run()
"""
from .app import MiniWSGI
from .request import Request
from .response import Response
from .router import Router, Route
from .exceptions import (
    HTTPException, BadRequest, Unauthorized, Forbidden,
    NotFound, MethodNotAllowed, InternalServerError,
)
from .middleware import Middleware, RequestLoggerMiddleware, ErrorHandlerMiddleware

__version__ = "1.0.0"
__all__ = [
    "MiniWSGI",
    "Request",
    "Response",
    "Router",
    "Route",
    "HTTPException",
    "BadRequest",
    "Unauthorized",
    "Forbidden",
    "NotFound",
    "MethodNotAllowed",
    "InternalServerError",
    "Middleware",
    "RequestLoggerMiddleware",
    "ErrorHandlerMiddleware",
]
