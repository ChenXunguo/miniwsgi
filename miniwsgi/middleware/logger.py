# -*- coding: utf-8 -*-
"""
请求日志中间件：记录每次请求的方法、路径、状态码、耗时。
使用标准库 logging，不依赖第三方库。
"""
import time
import logging
from .base import Middleware

logger = logging.getLogger("miniwsgi.access")


class RequestLoggerMiddleware(Middleware):
    """
    请求日志中间件。
    记录格式：[时间] METHOD PATH -> STATUS (耗时ms) [客户端IP]
    """

    def __init__(self, next_handler, log_level=logging.INFO):
        super().__init__(next_handler)
        self.log_level = log_level
        # 确保 logger 有 handler（首次使用时配置）
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

    def __call__(self, request):
        """重写 __call__ 以精确计时（包含整个下游链的耗时）"""
        start = time.time()
        try:
            response = self.next(request)
            status = response.status
            return response
        except Exception as e:
            status = 500
            raise
        finally:
            duration_ms = (time.time() - start) * 1000
            client = request.remote_addr or "-"
            logger.log(
                self.log_level,
                f"{request.method} {request.path} -> {status} "
                f"({duration_ms:.1f}ms) [{client}]"
            )
