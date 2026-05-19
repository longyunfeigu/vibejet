# Sentry 集成与监控 - FastAPI 实战

将原有 TypeScript/Sentry v8 指南等价映射为 Python/FastAPI 实现，覆盖错误捕获、性能监控、上下文丰富、PII 脱敏、Cron/后台任务监控与常见误区。示例均为生产可用。

## 目录

- 核心原则
- 初始化与配置（instrument.py）
- 错误捕获模式（控制器/服务/全局）
- 性能监控（Transactions/Spans/DB）
- Cron/后台任务监控
- 上下文与 PII 脱敏
- 常见错误与规避

---

## 核心原则

- 所有未处理异常必须进入 Sentry（全局异常处理器或集成自动捕获）。
- 默认开启性能采样（traces/profiles）并按环境调整采样率。
- 严格脱敏：请求头/用户 PII 清洗；健康检查与无意义错误过滤。

---

## 初始化与配置（instrument.py）

建议创建 `instrument.py` 并在应用启动“尽早导入”。示例：

```python
# instrument.py
from __future__ import annotations

import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

SENTRY_DSN = os.getenv("SENTRY_DSN")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
PROFILES_SAMPLE_RATE = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))
SERVICE_NAME = os.getenv("SERVICE_NAME", "fastapi-app")
RELEASE = os.getenv("RELEASE", "1.0.0")

def _before_send(event, hint):
    # 过滤健康检查
    req = event.get("request") or {}
    url = (req.get("url") or "").lower()
    if "/health" in url or "/healthz" in url or "/openapi.json" in url:
        return None

    # 脱敏 headers
    headers = req.get("headers") or {}
    for k in ["authorization", "cookie", "x-api-key", "x-forwarded-for"]:
        if k in headers:
            headers[k] = "[Filtered]"
    if headers:
        event.setdefault("request", {})["headers"] = headers

    # 脱敏 user 邮箱
    user = event.get("user") or {}
    email = user.get("email")
    if isinstance(email, str) and "@" in email and len(email) > 3:
        name, _, domain = email.partition("@")
        user["email"] = (name[:2] + "***@" + domain) if name else "***@" + domain
        event["user"] = user
    return event

def init_sentry() -> None:
    if not SENTRY_DSN:
        return
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENVIRONMENT,
        release=RELEASE,
        traces_sample_rate=TRACES_SAMPLE_RATE,
        profiles_sample_rate=PROFILES_SAMPLE_RATE,
        before_send=_before_send,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            LoggingIntegration(level=None, event_level=None),  # 仅作为面包屑
        ],
    )
    # 全局标签/上下文
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("service", SERVICE_NAME)
```

在 `main.py` 的最顶端导入：

```python
import instrument  # noqa: F401  确保尽早初始化（或 from instrument import init_sentry; init_sentry()）
from instrument import init_sentry
init_sentry()
```

环境变量示例：

```
SENTRY_DSN=your-dsn
ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.2
SENTRY_PROFILES_SAMPLE_RATE=0.1
SERVICE_NAME=fastapi-forge
RELEASE=1.2.3
```

---

## 错误捕获模式（控制器/服务/全局）

全局异常处理器（与 `fastapi-forge/core/exceptions.py` 一致）：

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import sentry_sdk

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def global_handler(_: Request, exc: Exception):
        sentry_sdk.capture_exception(exc)
        return JSONResponse(status_code=500, content={"code": "INTERNAL", "message": "Internal server error"})
```

服务层：捕获后抛出，让控制器/全局处理器统一转换为 HTTP 语义：

```python
import sentry_sdk

async def perform_operation():
    try:
        ...
    except SomeClientError as e:
        sentry_sdk.capture_exception(e)
        raise
```

控制器：若采用“统一响应包”，可在冲突/未找到等业务异常处添加 tags/context 后抛出：

```python
import sentry_sdk

with sentry_sdk.push_scope() as scope:
    scope.set_tag("controller", "UserController")
    scope.set_context("operation", {"name": "create", "entity": "user"})
    sentry_sdk.capture_exception(err)
```

---

## 性能监控（Transactions/Spans/DB）

- HTTP 入口：FastApiIntegration 会自动创建 server transaction
- DB：SqlalchemyIntegration 自动埋点 SQL（语句作为 breadcrumbs/spans）
- 业务自定义：使用 `start_span`/`start_transaction` 标注关键路径

```python
import sentry_sdk

async def create_user_flow():
    with sentry_sdk.start_transaction(name="user.create", op="flow"):
        with sentry_sdk.start_span(op="validate", description="validate payload"):
            ...
        with sentry_sdk.start_span(op="db", description="insert user"):
            ...  # 调用仓储
        with sentry_sdk.start_span(op="email", description="send welcome"):
            ...
```

自定义指标（可选）：

```python
try:
    from sentry_sdk import metrics
    metrics.gauge("user.create.duration_ms", 123.4, unit="millisecond")
except Exception:
    pass
```

---

## Cron/后台任务监控

在 CLI/Worker/Cron 中也应初始化 Sentry，并以 transaction 包裹任务：

```python
#!/usr/bin/env python3
from instrument import init_sentry
import sentry_sdk

init_sentry()

def main() -> int:
    with sentry_sdk.start_transaction(name="cron.reconcile", op="cron"):
        try:
            # 业务逻辑
            return 0
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return 1

raise SystemExit(main())
```

FastAPI BackgroundTasks/asyncio.create_task 也会被 Sentry 捕获；建议给任务添加 `done_callback` 记录异常，避免静默失败。

---

## 上下文与 PII 脱敏

丰富上下文（用户、标签、结构化上下文、面包屑）：

```python
import sentry_sdk

with sentry_sdk.push_scope() as scope:
    scope.set_user({"id": str(user.id), "email": user.email})
    scope.set_tag("endpoint", "/api/v1/users")
    scope.set_context("operation", {"type": "workflow.complete", "step": 3})
    sentry_sdk.add_breadcrumb(category="workflow", message="Starting step", level="info", data={"step": 3})
    sentry_sdk.capture_exception(error)
```

PII 保护：
- `before_send` 中移除 `authorization/cookie/X-API-Key` 等敏感头
- 邮箱脱敏（前两位 + ***）
- 避免将密码/令牌写入 `extra`

---

## 常见错误与规避

```text
❌ 忽略初始化顺序：Sentry 应在应用启动“尽早”初始化（instrument.py 最先导入）
❌ 未清洗 PII：Authorization/Cookie 原样上报
❌ 无性能采样：traces/profiles 皆为 0，难以排查慢查询与热点
❌ 吞掉异常：服务层捕获后未 re-raise 导致 200 假成功
❌ 健康检查噪音：/health /openapi.json 产生大量无意义事件
❌ 依赖日志替代监控：日志不等于错误追踪与性能可视化
```

