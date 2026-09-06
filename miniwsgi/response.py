# -*- coding: utf-8 -*-
"""
Response 类：封装 HTTP 响应，提供 WSGI 兼容的输出。
支持 JSON / 文本 / HTML 响应，可设置响应头、Cookie、状态码。
"""
import json
from .exceptions import STATUS_PHRASES


class Response:
    """
    HTTP 响应对象。
    视图函数可以直接返回 Response，也可以返回 dict/list/str/tuple，
    由 App 自动转换为 Response。
    """

    def __init__(self, body="", status=200, headers=None,
                 content_type="text/plain; charset=utf-8"):
        self._body = body
        self.status = status
        self.headers = dict(headers) if headers else {}
        self.content_type = content_type
        self._cookies = []

    # ---------- body 处理 ----------
    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, value):
        self._body = value

    def _encode_body(self):
        """将 body 编码为 bytes，供 WSGI 输出"""
        if isinstance(self._body, bytes):
            return self._body
        if isinstance(self._body, (dict, list)):
            return json.dumps(self._body, ensure_ascii=False).encode("utf-8")
        return str(self._body).encode("utf-8")

    # ---------- 便捷构造方法 ----------
    @classmethod
    def json(cls, data, status=200, headers=None):
        """构造 JSON 响应"""
        resp = cls(body=json.dumps(data, ensure_ascii=False), status=status,
                    content_type="application/json; charset=utf-8", headers=headers)
        return resp

    @classmethod
    def text(cls, text, status=200, headers=None):
        """构造纯文本响应"""
        return cls(body=str(text), status=status,
                   content_type="text/plain; charset=utf-8", headers=headers)

    @classmethod
    def html(cls, html_content, status=200, headers=None):
        """构造 HTML 响应"""
        return cls(body=html_content, status=status,
                   content_type="text/html; charset=utf-8", headers=headers)

    @classmethod
    def redirect(cls, location, status=302):
        """构造重定向响应"""
        return cls(body="", status=status, headers={"Location": location})

    # ---------- 响应头 / Cookie ----------
    def set_header(self, key, value):
        self.headers[key] = value

    def set_cookie(self, key, value, max_age=None, path="/",
                   domain=None, secure=False, httponly=False):
        """设置 Set-Cookie 响应头"""
        parts = [f"{key}={value}"]
        if max_age is not None:
            parts.append(f"Max-Age={max_age}")
        if path:
            parts.append(f"Path={path}")
        if domain:
            parts.append(f"Domain={domain}")
        if secure:
            parts.append("Secure")
        if httponly:
            parts.append("HttpOnly")
        self._cookies.append("; ".join(parts))

    # ---------- WSGI 输出 ----------
    @property
    def status_line(self):
        """WSGI 要求的状态行：'200 OK'"""
        phrase = STATUS_PHRASES.get(self.status, "Unknown")
        return f"{self.status} {phrase}"

    def get_wsgi_headers(self):
        """返回 WSGI start_response 需要的 (header_name, header_value) 列表"""
        headers = list(self.headers.items())
        # 确保 Content-Type
        has_content_type = any(k.lower() == "content-type" for k, _ in headers)
        if not has_content_type:
            headers.append(("Content-Type", self.content_type))
        # Cookie
        for cookie in self._cookies:
            headers.append(("Set-Cookie", cookie))
        return headers

    def get_body_iter(self):
        """返回 WSGI 可迭代 body（bytes）"""
        return [self._encode_body()]

    def __repr__(self):
        return f"<Response {self.status} {self.content_type}>"
