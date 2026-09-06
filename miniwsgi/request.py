# -*- coding: utf-8 -*-
"""
Request 类：封装 WSGI environ，提供便捷的请求属性访问。
负责解析请求方法、路径、查询参数、请求头、请求体（JSON/Form/原始）、Cookie。
"""
import json
from urllib.parse import parse_qs


class Request:
    """
    HTTP 请求对象。
    由 WSGI environ 构造，所有属性均为惰性解析（用到时才解析，避免不必要开销）。
    """

    def __init__(self, environ):
        self.environ = environ
        # 基础信息直接从 environ 取
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        # PEP 3333: PATH_INFO 是 native string，按 latin-1 解码自 URL 的 UTF-8 字节；
        # 需要重新编码为 latin-1 再解码为 UTF-8，才能得到正确的中文路径
        raw_path = environ.get("PATH_INFO", "/")
        try:
            self.path = raw_path.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            self.path = raw_path
        self.query_string = environ.get("QUERY_STRING", "")
        self.server_protocol = environ.get("SERVER_PROTOCOL", "HTTP/1.1")
        self.remote_addr = environ.get("REMOTE_ADDR", "")

        # 惰性解析的缓存
        self._headers = None
        self._args = None
        self._form = None
        self._json = None
        self._body = None
        self._cookies = None

    # ---------- 请求头 ----------
    @property
    def headers(self):
        """解析所有 HTTP 请求头（WSGI 中以 HTTP_ 前缀存储）"""
        if self._headers is None:
            self._headers = {}
            for key, value in self.environ.items():
                if key.startswith("HTTP_"):
                    # HTTP_CONTENT_TYPE → Content-Type
                    header_name = key[5:].replace("_", "-").title()
                    self._headers[header_name] = value
                elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                    header_name = key.replace("_", "-").title()
                    self._headers[header_name] = value
        return self._headers

    @property
    def content_type(self):
        return self.headers.get("Content-Type", "")

    @property
    def content_length(self):
        try:
            return int(self.environ.get("CONTENT_LENGTH", 0) or 0)
        except (ValueError, TypeError):
            return 0

    # ---------- 查询参数 ----------
    @property
    def args(self):
        """解析 URL 查询参数（?key=value），返回 dict（单值）"""
        if self._args is None:
            parsed = parse_qs(self.query_string, keep_blank_values=True)
            self._args = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
        return self._args

    # ---------- 请求体 ----------
    @property
    def body(self):
        """原始请求体（bytes）"""
        if self._body is None:
            length = self.content_length
            wsgi_input = self.environ.get("wsgi.input")
            if wsgi_input and length > 0:
                self._body = wsgi_input.read(length)
            else:
                self._body = b""
        return self._body

    @property
    def json(self):
        """解析 JSON 请求体，失败返回 None"""
        if self._json is None:
            if "application/json" in self.content_type and self.body:
                try:
                    self._json = json.loads(self.body.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self._json = None
        return self._json

    @property
    def form(self):
        """解析表单请求体（application/x-www-form-urlencoded）"""
        if self._form is None:
            self._form = {}
            if "application/x-www-form-urlencoded" in self.content_type and self.body:
                try:
                    parsed = parse_qs(self.body.decode("utf-8"), keep_blank_values=True)
                    self._form = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
                except UnicodeDecodeError:
                    pass
        return self._form

    # ---------- Cookie ----------
    @property
    def cookies(self):
        """解析 Cookie"""
        if self._cookies is None:
            self._cookies = {}
            cookie_header = self.headers.get("Cookie", "")
            if cookie_header:
                for pair in cookie_header.split(";"):
                    pair = pair.strip()
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        self._cookies[key.strip()] = value.strip()
        return self._cookies

    def __repr__(self):
        return f"<Request {self.method} {self.path}>"
