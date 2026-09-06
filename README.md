# MiniWSGI — 轻量级 WSGI Web 框架

> 遵循 PEP 3333 规范从零实现的轻量级 Web 框架，零第三方依赖，仅使用 Python 标准库。
> 用于深入理解 Web 框架底层原理，也可作为极轻量部署场景的备选方案。

## 项目定位

这是一个**技术探索项目**，目标是手写一个可用的 WSGI 框架，深刻理解：



* WSGI 协议（environ /start\_response/ 可迭代 body）

* HTTP 请求解析与响应封装

* 基于正则表达式的动态路由匹配

* 责任链模式的中间件机制

* 全局异常捕获与统一错误响应

**与 Flask 的关系**：项目 2 的预测 API 最终选用 Flask 以保证生产稳定性与生态完整性；本框架为后续需要极轻量部署的场景提供备选方案，同时加深了对 Flask 等成熟框架内部机制的理解。

## 技术栈



* **Python**（标准库：wsgiref, re, json, urllib.parse, logging, io, time）

* **WSGI**（PEP 3333）

* **装饰器**（路由注册）

* **正则表达式**（动态路由匹配）

* **责任链模式**（中间件机制）

## 核心功能

### 1. HTTP 请求解析（Request）



* 请求方法、路径、查询参数

* 请求头解析（HTTP\_ 前缀转换）

* 请求体解析：JSON / Form / 原始 bytes

* Cookie 解析

* 中文路径自动解码（PEP 3333 latin-1 → UTF-8）

### 2. 响应封装（Response）



* JSON / 文本 / HTML / 重定向 便捷构造

* 自定义响应头、Cookie 设置

* 状态码与标准原因短语

* WSGI 兼容输出（status\_line + headers + body iter）

### 3. 动态路由（Router）



* 静态路径：`/hello`

* 简单参数：`/user/<name>`

* 类型参数：`/user/<int:id>`、`/price/<float:p>`、`/files/<path:sub>`

* 原始正则：`^/archive/(?P<year>\d{4})$`

* 404（路径不匹配）/ 405（方法不允许）自动区分

### 4. 中间件机制（责任链模式）



* 基类 `Middleware`，提供 `process_request` / `process_response` 钩子

* 支持短路（process\_request 返回 Response 直接响应）

* 按注册顺序从外到内包裹，执行顺序可预测

* 内置中间件：


  * `RequestLoggerMiddleware`：请求日志（方法、路径、状态、耗时、客户端 IP）

  * `ErrorHandlerMiddleware`：全局异常捕获，统一 JSON 错误响应，debug 模式含堆栈

### 5. 视图返回值自动转换

视图函数可返回：



* `Response` 对象 → 直接使用

* `dict` / `list` → 自动 JSON 响应

* `str` → 自动文本响应

* `tuple` → `(body, status)` 或 `(body, status, headers)`

* `bytes` → 二进制响应

## 快速开始

### 最小示例



```
from miniwsgi import MiniWSGI, Response

app = MiniWSGI()

@app.route("/")

def index(request):

&#x20;   return {"message": "Hello, MiniWSGI!"}

@app.route("/user/\<int:user\_id>")

def get\_user(request, user\_id):

&#x20;   return Response.json({"id": user\_id, "name": "张三"})

@app.route("/echo", methods=\["POST"])

def echo(request):

&#x20;   return {"received": request.json}

if \_\_name\_\_ == "\_\_main\_\_":

&#x20;   app.run(host="127.0.0.1", port=8000)
```

### 运行示例



```
\# 演示应用（含8个接口）

python examples/demo\_app.py

\# 项目2气温预测API（MiniWSGI版本，需项目2环境）

python examples/temp\_predict\_api.py
```

### 运行测试



```
\# 使用 unittest（无需额外安装）

python -m unittest tests.test\_framework -v

\# 或使用 pytest（需安装）

python -m pytest tests/test\_framework.py -v
```

## API 文档

### 路由装饰器



```
@app.route(pattern, methods=None, name=None)
```



| 参数      | 类型   | 说明                                                        |
| ------- | ---- | --------------------------------------------------------- |
| pattern | str  | 路径模式，支持 `<name>`、`<int:id>`、`<float:p>`、`<path:sub>`、原始正则 |
| methods | list | 允许的 HTTP 方法，默认 `["GET"]`                                  |
| name    | str  | 路由名称，默认使用函数名                                              |

### Request 对象



| 属性                     | 说明                    |
| ---------------------- | --------------------- |
| `request.method`       | HTTP 方法（GET/POST/...） |
| `request.path`         | 请求路径（已解码中文）           |
| `request.args`         | 查询参数字典                |
| `request.headers`      | 请求头字典                 |
| `request.json`         | JSON 请求体（dict 或 None） |
| `request.form`         | 表单请求体字典               |
| `request.body`         | 原始请求体（bytes）          |
| `request.cookies`      | Cookie 字典             |
| `request.content_type` | Content-Type          |
| `request.remote_addr`  | 客户端 IP                |

### Response 对象



```
Response.json(data, status=200, headers=None)   # JSON 响应

Response.text(text, status=200, headers=None)    # 文本响应

Response.html(html, status=200, headers=None)    # HTML 响应

Response.redirect(location, status=302)           # 重定向

resp.set\_header(key, value)       # 设置响应头

resp.set\_cookie(key, value, ...)  # 设置 Cookie
```

### 自定义中间件



```
from miniwsgi import Middleware, Response

class AuthMiddleware(Middleware):

&#x20;   def process\_request(self, request):

&#x20;       token = request.headers.get("Authorization")

&#x20;       if not token:

&#x20;           return Response.json({"error": "Unauthorized"}, status=401)

&#x20;       return None  # 继续向下传递

&#x20;   def process\_response(self, request, response):

&#x20;       response.set\_header("X-Processed-By", "AuthMiddleware")

&#x20;       return response

app.add\_middleware(AuthMiddleware)
```

### 异常处理



```
from miniwsgi import NotFound, BadRequest, MethodNotAllowed

@app.route("/item/\<int:item\_id>")

def get\_item(request, item\_id):

&#x20;   if item\_id not in store:

&#x20;       raise NotFound(f"Item {item\_id} not found")

&#x20;   if not request.args.get("token"):

&#x20;       raise BadRequest("缺少 token 参数")

&#x20;   return store\[item\_id]
```

所有未捕获异常由 `ErrorHandlerMiddleware` 统一处理，返回：



```
{

&#x20; "error": "Internal Server Error",

&#x20; "status": 500,

&#x20; "error\_id": "ERR-12345"

}
```

## 项目结构



```
miniwsgi/

├── miniwsgi/                    # 框架核心包

│   ├── \_\_init\_\_.py              # 公共 API 导出

│   ├── app.py                   # MiniWSGI 应用类（WSGI入口、路由、中间件链）

│   ├── request.py               # Request 请求解析

│   ├── response.py              # Response 响应封装

│   ├── router.py                # Router 正则路由匹配

│   ├── exceptions.py            # HTTP 异常类 + 状态码短语

│   └── middleware/              # 中间件包

│       ├── \_\_init\_\_.py

│       ├── base.py              # Middleware 基类（责任链）

│       ├── logger.py            # 请求日志中间件

│       └── error\_handler.py     # 全局异常捕获中间件

├── examples/

│   ├── demo\_app.py              # 演示应用（8个接口）

│   └── temp\_predict\_api.py      # 项目2气温预测API（MiniWSGI版本）

├── tests/

│   └── test\_framework.py        # 单元测试（37个测试用例）

├── requirements.txt

└── README.md
```

## WSGI 工作原理



```
客户端请求

&#x20;   │

&#x20;   ▼

WSGI 服务器 (wsgiref / gunicorn / waitress)

&#x20;   │  environ dict + start\_response callback

&#x20;   ▼

MiniWSGI.\_\_call\_\_(environ, start\_response)

&#x20;   │

&#x20;   ├─ Request(environ)  ← 解析请求

&#x20;   │

&#x20;   ├─ 中间件链（责任链）

&#x20;   │   ├─ ErrorHandlerMiddleware  ← 最外层，捕获所有异常

&#x20;   │   ├─ RequestLoggerMiddleware ← 记录日志和耗时

&#x20;   │   ├─ 自定义中间件...

&#x20;   │   └─ router\_handler           ← 最内层，路由匹配 + 调用视图

&#x20;   │

&#x20;   ├─ Response  ← 视图返回值自动转换

&#x20;   │

&#x20;   └─ start\_response(status\_line, headers) + body\_iter

&#x20;        │

&#x20;        ▼

&#x20;   WSGI 服务器 → HTTP 响应 → 客户端
```

## 验证结果



* **单元测试**：37 个测试用例全部通过（Request/Response/Router/App/ 中间件 / 集成）

* **真实 HTTP 验证**：demo 应用 8 个接口全部正常（含中文路径、POST JSON、404/405/500、Cookie、自定义中间件响应头）

* **项目 2 预测 API**：使用 MiniWSGI 替代 Flask，`/health`、`/model_info`、`/predict` 三个接口全部正常，预测结果与 Flask 版一致

## 局限性与后续方向



* **并发模型**：开发服务器 wsgiref 为单线程，生产环境需配合 gunicorn/waitress

* **缺少静态文件服务**：当前不支持直接 serve 静态文件

* **缺少模板引擎**：不包含 Jinja2 等模板渲染

* **缺少表单文件上传**：不支持 multipart/form-data 文件上传

* **缺少会话管理**：无内置 session 机制

* **缺少 ASGI 支持**：仅 WSGI，不支持异步

## 许可证

MIT