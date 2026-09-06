# -*- coding: utf-8 -*-
"""
中间件基类：责任链模式（Chain of Responsibility）。

每个中间件持有下一个处理者（next），在 __call__ 中：
  1. process_request(request) —— 请求预处理，返回非 None 则短路直接响应
  2. self.next(request)        —— 调用链中下一个处理者
  3. process_response(request, response) —— 响应后处理

中间件按注册顺序从外到内包裹，最内层是路由分发器。
执行顺序：
  MW1.process_request → MW2.process_request → ... → 路由/视图
  MW1.process_response ← MW2.process_response ← ... ← 视图返回
"""


class Middleware:
    """中间件基类，所有自定义中间件继承此类"""

    def __init__(self, next_handler):
        """
        Args:
            next_handler: 链中的下一个处理者（中间件或路由分发器）
        """
        self.next = next_handler

    def __call__(self, request):
        """
        中间件主入口。默认实现：请求预处理 → 调用下一个 → 响应后处理。
        子类可重写 __call__ 实现更复杂的逻辑（如异常捕获、计时）。
        """
        response = self.process_request(request)
        if response is not None:
            return response
        response = self.next(request)
        return self.process_response(request, response)

    def process_request(self, request):
        """
        请求预处理钩子。
        返回 Response 对象则短路（不再调用后续中间件和视图）；
        返回 None 则继续向下传递。
        """
        return None

    def process_response(self, request, response):
        """
        响应后处理钩子。可以修改、替换响应对象。
        必须返回 Response 对象。
        """
        return response

    def __repr__(self):
        return f"<{self.__class__.__name__}>"
