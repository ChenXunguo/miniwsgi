# -*- coding: utf-8 -*-
"""
MiniWSGI 框架单元测试。
覆盖：Request 解析、Response 封装、Router 路由匹配、App WSGI 流程、
      中间件责任链、异常处理、返回值自动转换。
运行：python -m pytest tests/test_framework.py  或  python tests/test_framework.py
"""
import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miniwsgi import (
    MiniWSGI, Request, Response, Router,
    NotFound, MethodNotAllowed, BadRequest, InternalServerError,
    Middleware, RequestLoggerMiddleware, ErrorHandlerMiddleware,
)


def make_environ(method="GET", path="/", query_string="",
                  body=None, content_type=None, headers=None):
    """构造模拟 WSGI environ"""
    import io
    env = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "SERVER_PROTOCOL": "HTTP/1.1",
        "SERVER_NAME": "test",
        "SERVER_PORT": "80",
        "REMOTE_ADDR": "127.0.0.1",
        "wsgi.input": io.BytesIO(body or b""),
        "wsgi.errors": io.BytesIO(),
        "wsgi.url_scheme": "http",
        "CONTENT_LENGTH": str(len(body)) if body else "0",
    }
    if content_type:
        env["CONTENT_TYPE"] = content_type
    if headers:
        for key, value in headers.items():
            env_key = "HTTP_" + key.upper().replace("-", "_")
            env[env_key] = value
    return env


def call_app(app, method="GET", path="/", **kwargs):
    """模拟一次完整的 WSGI 请求，返回 (status, headers, body)"""
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    environ = make_environ(method=method, path=path, **kwargs)
    body_iter = app(environ, start_response)
    body = b"".join(body_iter)
    return captured["status"], captured["headers"], body


# ============================================================
# 1. Request 测试
# ============================================================
class TestRequest(unittest.TestCase):
    def test_basic_info(self):
        req = Request(make_environ("POST", "/api/test", "q=hello"))
        self.assertEqual(req.method, "POST")
        self.assertEqual(req.path, "/api/test")
        self.assertEqual(req.query_string, "q=hello")

    def test_query_args(self):
        req = Request(make_environ(query_string="name=张三&age=25&tags=a&tags=b"))
        self.assertEqual(req.args["name"], "张三")
        self.assertEqual(req.args["age"], "25")
        self.assertEqual(req.args["tags"], ["a", "b"])

    def test_headers(self):
        req = Request(make_environ(headers={"X-Custom": "value", "Authorization": "Bearer xxx"}))
        self.assertEqual(req.headers["X-Custom"], "value")
        self.assertEqual(req.headers["Authorization"], "Bearer xxx")

    def test_json_body(self):
        body = json.dumps({"key": "value", "num": 42}).encode("utf-8")
        req = Request(make_environ("POST", body=body, content_type="application/json"))
        self.assertEqual(req.json, {"key": "value", "num": 42})

    def test_form_body(self):
        body = b"username=test&password=123456"
        req = Request(make_environ("POST", body=body,
                                    content_type="application/x-www-form-urlencoded"))
        self.assertEqual(req.form["username"], "test")
        self.assertEqual(req.form["password"], "123456")

    def test_cookies(self):
        req = Request(make_environ(headers={"Cookie": "session=abc123; user=test"}))
        self.assertEqual(req.cookies["session"], "abc123")
        self.assertEqual(req.cookies["user"], "test")

    def test_empty_body(self):
        req = Request(make_environ("GET"))
        self.assertEqual(req.body, b"")
        self.assertIsNone(req.json)


# ============================================================
# 2. Response 测试
# ============================================================
class TestResponse(unittest.TestCase):
    def test_json_response(self):
        resp = Response.json({"msg": "ok"})
        self.assertEqual(resp.status, 200)
        self.assertIn("application/json", resp.content_type)
        body = resp._encode_body()
        self.assertEqual(json.loads(body), {"msg": "ok"})

    def test_text_response(self):
        resp = Response.text("hello")
        self.assertIn("text/plain", resp.content_type)
        self.assertEqual(resp._encode_body(), b"hello")

    def test_html_response(self):
        resp = Response.html("<h1>hi</h1>")
        self.assertIn("text/html", resp.content_type)

    def test_status_line(self):
        resp = Response(status=404)
        self.assertEqual(resp.status_line, "404 Not Found")
        resp2 = Response(status=500)
        self.assertEqual(resp2.status_line, "500 Internal Server Error")

    def test_headers_and_cookies(self):
        resp = Response.text("ok")
        resp.set_header("X-Custom", "value")
        resp.set_cookie("sid", "abc", max_age=3600, httponly=True)
        wsgi_headers = resp.get_wsgi_headers()
        header_dict = dict(wsgi_headers)
        self.assertEqual(header_dict["X-Custom"], "value")
        self.assertIn("sid=abc", header_dict["Set-Cookie"])
        self.assertIn("HttpOnly", header_dict["Set-Cookie"])

    def test_redirect(self):
        resp = Response.redirect("/new-url")
        self.assertEqual(resp.status, 302)
        self.assertEqual(dict(resp.get_wsgi_headers())["Location"], "/new-url")


# ============================================================
# 3. Router 测试
# ============================================================
class TestRouter(unittest.TestCase):
    def setUp(self):
        self.router = Router()

    def test_static_route(self):
        def handler(request): pass
        self.router.add_route("GET", "/hello", handler)
        h, kwargs = self.router.match("GET", "/hello")
        self.assertIs(h, handler)
        self.assertEqual(kwargs, {})

    def test_dynamic_param(self):
        def handler(request, name): pass
        self.router.add_route("GET", "/user/<name>", handler)
        h, kwargs = self.router.match("GET", "/user/张三")
        self.assertEqual(kwargs["name"], "张三")

    def test_int_param(self):
        def handler(request, user_id): pass
        self.router.add_route("GET", "/user/<int:user_id>", handler)
        h, kwargs = self.router.match("GET", "/user/123")
        self.assertEqual(kwargs["user_id"], 123)
        self.assertIsInstance(kwargs["user_id"], int)

    def test_float_param(self):
        def handler(request, price): pass
        self.router.add_route("GET", "/price/<float:price>", handler)
        h, kwargs = self.router.match("GET", "/price/19.99")
        self.assertAlmostEqual(kwargs["price"], 19.99)

    def test_path_param(self):
        def handler(request, subpath): pass
        self.router.add_route("GET", "/files/<path:subpath>", handler)
        h, kwargs = self.router.match("GET", "/files/a/b/c.txt")
        self.assertEqual(kwargs["subpath"], "a/b/c.txt")

    def test_regex_route(self):
        def handler(request, year): pass
        self.router.add_route("GET", r"^/archive/(?P<year>\d{4})$", handler)
        h, kwargs = self.router.match("GET", "/archive/2024")
        self.assertEqual(kwargs["year"], "2024")

    def test_not_found(self):
        with self.assertRaises(NotFound):
            self.router.match("GET", "/nonexistent")

    def test_method_not_allowed(self):
        def handler(request): pass
        self.router.add_route("GET", "/api", handler)
        with self.assertRaises(MethodNotAllowed):
            self.router.match("POST", "/api")

    def test_multiple_methods(self):
        def get_handler(request): pass
        def post_handler(request): pass
        self.router.add_route("GET", "/api", get_handler)
        self.router.add_route("POST", "/api", post_handler)
        h1, _ = self.router.match("GET", "/api")
        h2, _ = self.router.match("POST", "/api")
        self.assertIs(h1, get_handler)
        self.assertIs(h2, post_handler)


# ============================================================
# 4. App / WSGI 流程测试
# ============================================================
class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = MiniWSGI()

    def test_route_decorator(self):
        @self.app.route("/test")
        def test_handler(request):
            return {"ok": True}

        status, headers, body = call_app(self.app, "GET", "/test")
        self.assertEqual(status, "200 OK")
        self.assertEqual(json.loads(body), {"ok": True})

    def test_dynamic_route_in_app(self):
        @self.app.route("/item/<int:item_id>")
        def item(request, item_id):
            return {"item_id": item_id}

        status, _, body = call_app(self.app, "GET", "/item/42")
        self.assertEqual(json.loads(body), {"item_id": 42})

    def test_return_tuple(self):
        @self.app.route("/created")
        def created(request):
            return {"id": 1}, 201

        status, _, body = call_app(self.app, "GET", "/created")
        self.assertEqual(status, "201 Created")
        self.assertEqual(json.loads(body), {"id": 1})

    def test_return_response_object(self):
        @self.app.route("/custom")
        def custom(request):
            resp = Response.text("custom response", status=202)
            resp.set_header("X-Test", "yes")
            return resp

        status, headers, body = call_app(self.app, "GET", "/custom")
        self.assertEqual(status, "202 Accepted")
        self.assertEqual(dict(headers)["X-Test"], "yes")
        self.assertEqual(body, b"custom response")

    def test_404_handling(self):
        status, _, body = call_app(self.app, "GET", "/missing")
        self.assertEqual(status, "404 Not Found")
        data = json.loads(body)
        self.assertEqual(data["status"], 404)
        self.assertIn("error", data)

    def test_405_handling(self):
        @self.app.route("/only-get")
        def only_get(request):
            return {"ok": True}

        status, _, body = call_app(self.app, "POST", "/only-get")
        self.assertEqual(status, "405 Method Not Allowed")

    def test_query_params_in_view(self):
        @self.app.route("/search")
        def search(request):
            return {"q": request.args.get("q", "")}

        status, _, body = call_app(self.app, "GET", "/search", query_string="q=test")
        self.assertEqual(json.loads(body), {"q": "test"})

    def test_post_json_in_view(self):
        @self.app.route("/echo", methods=["POST"])
        def echo(request):
            return {"received": request.json}

        payload = {"key": "value"}
        status, _, body = call_app(
            self.app, "POST", "/echo",
            body=json.dumps(payload).encode(),
            content_type="application/json"
        )
        self.assertEqual(json.loads(body), {"received": payload})

    def test_unhandled_exception_500(self):
        @self.app.route("/boom")
        def boom(request):
            raise ValueError("something broke")

        status, _, body = call_app(self.app, "GET", "/boom")
        self.assertEqual(status, "500 Internal Server Error")
        data = json.loads(body)
        self.assertEqual(data["status"], 500)
        self.assertIn("error_id", data)

    def test_bad_request_exception(self):
        @self.app.route("/bad")
        def bad(request):
            raise BadRequest("invalid input")

        status, _, body = call_app(self.app, "GET", "/bad")
        self.assertEqual(status, "400 Bad Request")
        self.assertEqual(json.loads(body)["error"], "invalid input")


# ============================================================
# 5. 中间件测试
# ============================================================
class TestMiddleware(unittest.TestCase):
    def test_custom_middleware(self):
        """测试自定义中间件能修改请求和响应"""
        app = MiniWSGI()

        class AddHeaderMiddleware(Middleware):
            def process_response(self, request, response):
                response.set_header("X-Middleware", "active")
                return response

        app.add_middleware(AddHeaderMiddleware)

        @app.route("/test")
        def test(request):
            return {"ok": True}

        status, headers, _ = call_app(app, "GET", "/test")
        self.assertEqual(dict(headers).get("X-Middleware"), "active")

    def test_middleware_short_circuit(self):
        """测试中间件在 process_request 中短路"""
        app = MiniWSGI()

        class BlockMiddleware(Middleware):
            def process_request(self, request):
                return Response.json({"blocked": True}, status=403)

        app.add_middleware(BlockMiddleware)

        @app.route("/test")
        def test(request):
            return {"ok": True}

        status, _, body = call_app(app, "GET", "/test")
        self.assertEqual(status, "403 Forbidden")
        self.assertEqual(json.loads(body), {"blocked": True})

    def test_middleware_chain_order(self):
        """测试中间件执行顺序（先注册的在外层，request 先执行，response 后执行）"""
        app = MiniWSGI()
        order = []

        class MW1(Middleware):
            def process_request(self, request):
                order.append("mw1_req")
                return None
            def process_response(self, request, response):
                order.append("mw1_resp")
                return response

        class MW2(Middleware):
            def process_request(self, request):
                order.append("mw2_req")
                return None
            def process_response(self, request, response):
                order.append("mw2_resp")
                return response

        app.add_middleware(MW1)
        app.add_middleware(MW2)

        @app.route("/test")
        def test(request):
            order.append("view")
            return {"ok": True}

        call_app(app, "GET", "/test")
        # 期望顺序：mw1_req → mw2_req → view → mw2_resp → mw1_resp
        self.assertEqual(order, ["mw1_req", "mw2_req", "view", "mw2_resp", "mw1_resp"])

    def test_error_handler_catches_exception(self):
        """测试 ErrorHandlerMiddleware 能捕获下游异常"""
        app = MiniWSGI()  # 默认已注册 ErrorHandlerMiddleware

        @app.route("/fail")
        def fail(request):
            raise RuntimeError("test error")

        status, _, body = call_app(app, "GET", "/fail")
        self.assertEqual(status, "500 Internal Server Error")
        data = json.loads(body)
        self.assertEqual(data["error"], "Internal Server Error")
        self.assertIn("error_id", data)


# ============================================================
# 6. 集成测试（完整请求生命周期）
# ============================================================
class TestIntegration(unittest.TestCase):
    def test_full_crud_like_flow(self):
        """模拟完整的 API 交互流程"""
        app = MiniWSGI()
        store = {}

        @app.route("/items", methods=["GET"])
        def list_items(request):
            return {"items": list(store.values())}

        @app.route("/items", methods=["POST"])
        def create_item(request):
            data = request.json or {}
            item_id = len(store) + 1
            store[item_id] = {"id": item_id, "name": data.get("name", "")}
            return store[item_id], 201

        @app.route("/items/<int:item_id>", methods=["GET"])
        def get_item(request, item_id):
            if item_id not in store:
                raise NotFound(f"Item {item_id} not found")
            return store[item_id]

        # 创建
        status, _, body = call_app(
            app, "POST", "/items",
            body=json.dumps({"name": "test item"}).encode(),
            content_type="application/json"
        )
        self.assertEqual(status, "201 Created")
        self.assertEqual(json.loads(body)["name"], "test item")

        # 列表
        status, _, body = call_app(app, "GET", "/items")
        self.assertEqual(len(json.loads(body)["items"]), 1)

        # 获取单个
        status, _, body = call_app(app, "GET", "/items/1")
        self.assertEqual(json.loads(body)["id"], 1)

        # 不存在
        status, _, body = call_app(app, "GET", "/items/999")
        self.assertEqual(status, "404 Not Found")


if __name__ == "__main__":
    unittest.main(verbosity=2)
