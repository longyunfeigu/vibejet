# input: 各子中间件模块
# output: HTTP 中间件公共导出
# owner: wanhua.gu
# pos: 表示层中间件 - 包入口与抽象规则说明；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""
HTTP 中间件包。

抽象规则：本目录下所有 HTTP 中间件统一使用 **纯 ASGI** 实现
（实现 ``async def __call__(self, scope, receive, send)``），
**禁止使用** ``starlette.middleware.base.BaseHTTPMiddleware``。

为什么不用 BaseHTTPMiddleware？

1. **请求体死锁风险**：BaseHTTPMiddleware 会接管 ``receive`` 通道。
   如果中间件内调用 ``request.body()`` / ``request.json()``，下游路由
   再次读取请求体时可能死锁或读到空 body（Starlette 的已知问题）。
2. **响应流劫持成本**：BaseHTTPMiddleware 会把整个响应缓冲成单一
   ``Response`` 对象再转发，破坏 StreamingResponse 的边读边写语义，
   增加内存占用并影响 SSE / chunked 响应。
3. **异常传播差异**：BaseHTTPMiddleware 把 ``call_next`` 异常包成
   ``RuntimeError("No response returned.")``，丢失原始堆栈，干扰
   全局异常处理器与 Sentry 上下文。
4. **统一抽象**：日志、metrics 等已采用纯 ASGI；多套抽象共存会让
   后续新增中间件的人无所适从。

新增中间件时请参考 ``logging.py`` / ``request_id.py`` / ``locale.py`` /
``metrics.py`` 的写法（receive/send wrapper 模式）。
"""

from .locale import LocaleMiddleware
from .logging import LoggingMiddleware
from .metrics import PrometheusMiddleware
from .request_id import RequestIDMiddleware, get_client_ip, get_request_id

__all__ = [
    "RequestIDMiddleware",
    "LocaleMiddleware",
    "LoggingMiddleware",
    "PrometheusMiddleware",
    "get_request_id",
    "get_client_ip",
]
