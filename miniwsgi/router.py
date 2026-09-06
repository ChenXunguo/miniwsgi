# -*- coding: utf-8 -*-
"""
Router：基于正则表达式的动态路由匹配器。
支持：
  - 静态路径：/hello
  - 简单参数：/user/<id>        → 匹配任意非斜杠字符
  - 类型参数：/user/<int:id>    → 匹配数字
             /item/<float:price> → 匹配浮点数
             /path/<path:sub>    → 匹配含斜杠的路径
  - 原始正则：以 ^ 开头或含 (?P< 的模式直接使用
匹配成功后提取命名分组作为视图函数的关键字参数。
"""
import re
from .exceptions import NotFound, MethodNotAllowed


# 类型转换器：类型名 → (正则片段, 转换函数)
CONVERTERS = {
    "int": (r"\d+", int),
    "float": (r"[\d.]+", float),
    "path": (r".+", str),
    "str": (r"[^/]+", str),
    "default": (r"[^/]+", str),
}

# 匹配 <name> 或 <type:name> 形式的参数占位符
PARAM_PATTERN = re.compile(r"<(?:(?P<type>\w+):)?(?P<name>\w+)>")


class Route:
    """单条路由规则"""

    def __init__(self, method, pattern, handler, name=None):
        self.method = method.upper()
        self.pattern = pattern
        self.handler = handler
        self.name = name or handler.__name__
        self.regex, self.param_names, self.converters = self._compile(pattern)

    def _compile(self, pattern):
        """
        将路径模式编译为正则表达式。
        如果模式以 ^ 开头或包含 (?P<，视为原始正则直接使用。
        """
        # 原始正则模式
        if pattern.startswith("^") or "(?P<" in pattern:
            regex = re.compile(pattern)
            param_names = list(regex.groupindex.keys())
            return regex, param_names, {}

        # 转换 <type:name> / <name> 为命名捕获组
        converters = {}
        param_names = []

        def replace_param(match):
            param_type = match.group("type") or "default"
            param_name = match.group("name")
            regex_fragment, converter = CONVERTERS.get(param_type, CONVERTERS["default"])
            converters[param_name] = converter
            param_names.append(param_name)
            return f"(?P<{param_name}>{regex_fragment})"

        compiled_pattern = PARAM_PATTERN.sub(replace_param, pattern)
        # 确保完整匹配（从开头到结尾）
        if not compiled_pattern.startswith("^"):
            compiled_pattern = "^" + compiled_pattern
        if not compiled_pattern.endswith("$"):
            compiled_pattern = compiled_pattern + "$"

        regex = re.compile(compiled_pattern)
        return regex, param_names, converters

    def match(self, method, path):
        """
        尝试匹配请求方法和路径。
        返回匹配到的参数字典，不匹配返回 None。
        """
        if method != self.method:
            return None
        match = self.regex.match(path)
        if match is None:
            return None
        # 对匹配到的参数做类型转换
        kwargs = {}
        for name, value in match.groupdict().items():
            converter = self.converters.get(name, str)
            try:
                kwargs[name] = converter(value)
            except (ValueError, TypeError):
                kwargs[name] = value
        return kwargs

    def __repr__(self):
        return f"<Route {self.method} {self.pattern} -> {self.name}>"


class Router:
    """路由表：管理所有路由规则，执行匹配"""

    def __init__(self):
        self.routes = []

    def add_route(self, method, pattern, handler, name=None):
        """注册一条路由"""
        route = Route(method, pattern, handler, name)
        self.routes.append(route)
        return route

    def match(self, method, path):
        """
        匹配路由，返回 (handler, kwargs)。
        路径匹配但方法不匹配 → 抛 MethodNotAllowed(405)
        完全不匹配 → 抛 NotFound(404)
        """
        method = method.upper()
        path_matched = False

        for route in self.routes:
            # 先用正则试匹配路径（不考虑方法）
            if route.regex.match(path):
                path_matched = True
                if route.method == method:
                    kwargs = route.match(method, path)
                    if kwargs is not None:
                        return route.handler, kwargs

        if path_matched:
            raise MethodNotAllowed(f"Method {method} not allowed for {path}")
        raise NotFound(f"No route for {method} {path}")

    def get_routes_info(self):
        """返回所有路由的简要信息（用于调试/文档）"""
        return [
            {"method": r.method, "pattern": r.pattern, "handler": r.name}
            for r in self.routes
        ]
