# -*- coding: utf-8 -*-
"""
MiniWSGI 框架演示应用。
展示：静态路由、动态参数路由、类型参数、查询参数、JSON 请求体、
     Cookie 设置、自定义中间件、404/405 处理。

运行：python examples/demo_app.py
访问：http://127.0.0.1:8000
"""
import sys
import os
import time

# 确保能导入 miniwsgi 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miniwsgi import MiniWSGI, Response, Middleware

app = MiniWSGI(debug=True)


# ========== 1. 静态路由 ==========
@app.route("/")
def index(request):
    """首页：返回 JSON"""
    return {
        "framework": "MiniWSGI",
        "version": "1.0.0",
        "message": "欢迎使用 MiniWSGI 轻量级 Web 框架",
        "endpoints": [
            "GET  /",
            "GET  /hello/<name>",
            "GET  /user/<int:user_id>",
            "GET  /search?q=keyword",
            "POST /echo",
            "GET  /cookie",
            "GET  /error",
            "GET  /slow",
        ],
    }


# ========== 2. 动态参数路由（简单参数） ==========
@app.route("/hello/<name>")
def hello(request, name):
    """带路径参数的路由"""
    return Response.json({
        "message": f"Hello, {name}!",
        "name": name,
        "method": request.method,
    })


# ========== 3. 类型参数路由 ==========
@app.route("/user/<int:user_id>")
def get_user(request, user_id):
    """int 类型参数，自动转换为整数"""
    # 模拟用户数据
    users = {
        1: {"id": 1, "name": "张三", "city": "昆明"},
        2: {"id": 2, "name": "李四", "city": "大理"},
        3: {"id": 3, "name": "王五", "city": "丽江"},
    }
    user = users.get(user_id)
    if user is None:
        # 主动抛出 404
        from miniwsgi import NotFound
        raise NotFound(f"用户 {user_id} 不存在")
    return Response.json(user)


# ========== 4. 查询参数 ==========
@app.route("/search")
def search(request):
    """读取 URL 查询参数 ?q=xxx&page=1"""
    keyword = request.args.get("q", "")
    page = int(request.args.get("page", "1"))
    return Response.json({
        "keyword": keyword,
        "page": page,
        "results": [f"{keyword} 结果{i}" for i in range(1, 4)] if keyword else [],
        "all_args": request.args,
    })


# ========== 5. POST JSON 请求体 ==========
@app.route("/echo", methods=["POST"])
def echo(request):
    """回显 JSON 请求体"""
    data = request.json
    if data is None:
        from miniwsgi import BadRequest
        raise BadRequest("请求体必须是有效的 JSON")
    return Response.json({
        "received": data,
        "content_type": request.content_type,
        "content_length": request.content_length,
    })


# ========== 6. 设置 Cookie ==========
@app.route("/cookie")
def set_cookie(request):
    """设置并读取 Cookie"""
    visit_count = int(request.cookies.get("visit_count", "0")) + 1
    resp = Response.json({
        "message": "这是你第 N 次访问",
        "visit_count": visit_count,
        "all_cookies": request.cookies,
    })
    resp.set_cookie("visit_count", str(visit_count), max_age=3600)
    resp.set_cookie("framework", "miniwsgi", max_age=3600)
    return resp


# ========== 7. 主动抛异常（测试全局异常捕获） ==========
@app.route("/error")
def trigger_error(request):
    """主动抛出未捕获异常，测试 ErrorHandlerMiddleware"""
    raise RuntimeError("这是一个测试用的未捕获异常")


# ========== 8. 自定义中间件示例 ==========
class TimingMiddleware(Middleware):
    """自定义中间件：在响应头中添加 X-Response-Time"""
    def __call__(self, request):
        start = time.time()
        response = self.next(request)
        duration_ms = (time.time() - start) * 1000
        response.set_header("X-Response-Time", f"{duration_ms:.2f}ms")
        return response


# 注册自定义中间件（在内置中间件之后注册，位于内层）
app.add_middleware(TimingMiddleware)


# ========== 启动 ==========
if __name__ == "__main__":
    app.list_routes()
    app.run(host="127.0.0.1", port=8000)
