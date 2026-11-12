from __future__ import annotations

from typing import TYPE_CHECKING, Optional, cast

from ..base import (
    ConsumeMiddleware,
    Envelope,
    HandleResult,
    Headers,
    PublishMiddleware,
    PublishResult,
)

if TYPE_CHECKING:
    from opentelemetry.propagators.textmap import Getter, Setter

try:
    from opentelemetry import trace
    from opentelemetry.trace import Tracer
except Exception:  # pragma: no cover - optional dependency
    trace = None
    Tracer = None  # type: ignore


# 鸭子类型适配器：实现 OTel Getter/Setter 接口但不继承其 ABC（opentelemetry 是可选依赖，
# 模块级继承会让未安装时 import 失败）；传给 inject/extract 时按接口 cast。
class _HdrGetter:
    def get(self, carrier: Headers, key: str) -> list[str]:
        v = carrier.get(key)
        return (
            [v.decode("utf-8")]
            if isinstance(v, (bytes, bytearray))
            else ([] if v is None else [str(v)])
        )

    def keys(self, carrier: Headers) -> list[str]:
        return list(carrier.keys())


class _HdrSetter:
    def set(self, carrier: Headers, key: str, value: str) -> None:
        carrier[key] = value.encode("utf-8")


class TracingMiddleware(PublishMiddleware, ConsumeMiddleware):
    def __init__(self, service_name: str = "messaging") -> None:
        self.enabled = trace is not None
        self.tracer: Optional[Tracer] = trace.get_tracer(service_name) if self.enabled else None
        self._getter = _HdrGetter()
        self._setter = _HdrSetter()

    def before_publish(self, topic: str, env: Envelope) -> Envelope:
        if not self.enabled or not self.tracer:
            return env
        with self.tracer.start_as_current_span("messaging.produce"):
            from opentelemetry.propagate import inject

            inject(env.headers, setter=cast("Setter[Headers]", self._setter))
        return env

    def after_publish(self, topic: str, env: Envelope, result: PublishResult) -> None:
        return

    def before_handle(self, topic: str, partition: int, offset: int, env: Envelope) -> Envelope:
        if not self.enabled or not self.tracer:
            return env
        from opentelemetry.propagate import extract

        ctx = extract(env.headers, getter=cast("Getter[Headers]", self._getter))
        _ = ctx
        return env

    def after_handle(
        self,
        topic: str,
        partition: int,
        offset: int,
        env: Envelope,
        result: HandleResult,
        exc: Optional[BaseException] = None,
    ) -> None:
        return
