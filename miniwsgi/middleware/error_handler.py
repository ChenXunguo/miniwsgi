# -*- coding: utf-8 -*-
"""
全局异常捕获中间件：
  - 捕获 HTTPException（404/405/400 等），返回统一 JSON 错误响应
  - 捕获未预期的 Exception，返回 500 JSON 错误响应，避免 WSGI 服务崩溃
  - 记录异常堆栈日志，便于调试
"""
import logging
import traceback
from .base import Middleware
from ..response import Response
from ..exceptions import HTTPException

logger = logging.getLogger("miniwsgi.error")


class ErrorHandlerMiddleware(Middleware):
    """
    全局异常处理中间件。
    应放在中间件链的最外层（最先注册），确保能捕获所有下游异常。
    """

    def __init__(self, next_handler, debug=False):
        super().__init__(next_handler)
        self.debug = debug  # debug 模式下在错误响应中包含堆栈信息

    def __call__(self, request):
        try:
            return self.next(request)
        except HTTPException as e:
            # 预期内的 HTTP 异常（404/405/400 等）
            logger.warning(f"HTTP {e.status_code}: {e.message} - {request.method} {request.path}")
            body = {
                "error": e.message,
                "status": e.status_code,
                "path": request.path,
            }
            return Response.json(body, status=e.status_code)
        except Exception as e:
            # 未预期的异常 → 500
            error_id = f"ERR-{id(e) % 100000:05d}"
            logger.error(
                f"Unhandled exception [{error_id}] at {request.method} {request.path}:\n"
                f"{traceback.format_exc()}"
            )
            body = {
                "error": "Internal Server Error",
                "status": 500,
                "error_id": error_id,
            }
            if self.debug:
                body["detail"] = traceback.format_exc()
            return Response.json(body, status=500)
