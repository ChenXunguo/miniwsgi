# -*- coding: utf-8 -*-
"""
MiniWSGI：遵循 PEP 3333 的轻量级 WSGI Web 框架。

核心能力：
  - HTTP 请求解析（Request）与响应封装（Response）
  - 基于正则表达式的动态路由匹配，支持 GET/POST/PUT/DELETE 等
  - 装饰器注册路由：@app.route("/path", methods=["GET"])
  - 责任链模式的可插拔中间件
  - 内置请求日志、全局异常捕获中间件
  - 零第三方依赖（仅标准库），可直接用 wsgiref 运行

使用示例：
    from miniwsgi import MiniWSGI, Response

    app = MiniWSGI()

    @app.route("/hello/<name>")
    def hello(request, name):
        return Response.json({"message": f"Hello, {name}!"})

    if __name__ == "__main__":
        app.run()
"""
from .request import Request
from .response import Response
from .router import Router
from .exceptions import HTTPException
from .middleware import RequestLoggerMiddleware, ErrorHandlerMiddleware


class MiniWSGI:
    """WSGI 应用主类"""

    def __init__(self, debug=False):
        self.router = Router()
        self.debug = debug
        # 中间件类列表（按注册顺序，从外到内包裹）
        self._middleware_classes = []
        # 构建好的中间件链（惰性构建，注册新中间件后失效）
        self._chain = None
        # 默认内置中间件
        self._setup_default_middleware()

    def _setup_default_middleware(self):
        """注册默认中间件：异常捕获（最外层）→ 请求日志"""
        self.add_middleware(ErrorHandlerMiddleware, debug=self.debug)
        self.add_middleware(RequestLoggerMiddleware)

    # ---------- 路由注册 ----------
    def route(self, pattern, methods=None, name=None):
        """
        路由装饰器。
        Args:
            pattern: 路径模式，支持 /static、/<param>、/<int:id>、原始正则
            methods: 允许的 HTTP 方法列表，默认 ["GET"]
            name: 路由名称，默认使用函数名
        """
        methods = methods or ["GET"]

        def decorator(func):
            for method in methods:
                self.router.add_route(method, pattern, func, name)
            return func

        return decorator

    def add_route(self, pattern, handler, methods=None, name=None):
        """编程式注册路由（非装饰器方式）"""
        methods = methods or ["GET"]
        for method in methods:
            self.router.add_route(method, pattern, handler, name)

    # ---------- 中间件管理 ----------
    def add_middleware(self, middleware_class, **kwargs):
        """
        注册中间件。按注册顺序从外到内包裹。
        Args:
            middleware_class: 中间件类（继承 Middleware）
            **kwargs: 传递给中间件构造函数的额外参数（除 next_handler 外）
        """
        self._middleware_classes.append((middleware_class, kwargs))
        self._chain = None  # 使缓存失效

    def _build_chain(self):
        """
        构建中间件责任链。
        最内层是路由分发器（router_handler），逐层向外包裹中间件。
        """
        def router_handler(request):
            """最内层处理者：路由匹配 → 调用视图函数 → 转换返回值为 Response"""
            handler, kwargs = self.router.match(request.method, request.path)
            result = handler(request, **kwargs)
            return self._convert_to_response(result)

        handler = router_handler
        # 逆序包裹：后注册的中间件在内层，先注册的在外层
        for mw_class, mw_kwargs in reversed(self._middleware_classes):
            handler = mw_class(handler, **mw_kwargs)
        return handler

    def _convert_to_response(self, result):
        """
        将视图函数的返回值转换为 Response 对象。
        支持返回：
          - Response 对象 → 直接使用
          - dict / list → JSON 响应
          - str → 纯文本响应
          - tuple → (body, status) 或 (body, status, headers)
          - bytes → 原始字节响应
          - 其他 → str() 后文本响应
        """
        if isinstance(result, Response):
            return result
        if isinstance(result, tuple):
            body = result[0]
            status = result[1] if len(result) > 1 else 200
            headers = result[2] if len(result) > 2 else None
            if isinstance(body, (dict, list)):
                return Response.json(body, status=status, headers=headers)
            if isinstance(body, str):
                return Response.text(body, status=status, headers=headers)
            return Response(body=body, status=status, headers=headers)
        if isinstance(result, (dict, list)):
            return Response.json(result)
        if isinstance(result, str):
            return Response.text(result)
        if isinstance(result, bytes):
            return Response(body=result, content_type="application/octet-stream")
        return Response.text(str(result))

    # ---------- WSGI 入口 ----------
    def __call__(self, environ, start_response):
        """
        WSGI 应用入口（PEP 3333）。
        Args:
            environ: WSGI 环境变量字典
            start_response: 开始响应的回调函数
        Returns:
            可迭代的 bytes 对象（响应体）
        """
        request = Request(environ)
        if self._chain is None:
            self._chain = self._build_chain()
        response = self._chain(request)
        start_response(response.status_line, response.get_wsgi_headers())
        return response.get_body_iter()

    # ---------- 开发服务器 ----------
    def run(self, host="127.0.0.1", port=8000):
        """
        使用 wsgiref.simple_server 启动开发服务器（仅用于开发/测试）。
        生产环境建议使用 gunicorn / uWSGI / waitress 等 WSGI 服务器。
        """
        from wsgiref.simple_server import make_server

        server = make_server(host, port, self)
        print(f"╔══════════════════════════════════════════╗")
        print(f"║  MiniWSGI 开发服务器已启动                ║")
        print(f"║  地址: http://{host}:{port}              ║")
        print(f"║  路由数: {len(self.router.routes)}                        ║")
        print(f"║  按 Ctrl+C 停止                           ║")
        print(f"╚══════════════════════════════════════════╝")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止。")
            server.server_close()

    # ---------- 调试辅助 ----------
    def list_routes(self):
        """打印所有已注册路由（调试用）"""
        print("已注册路由：")
        for info in self.router.get_routes_info():
            print(f"  {info['method']:<6} {info['pattern']:<30} -> {info['handler']}")
