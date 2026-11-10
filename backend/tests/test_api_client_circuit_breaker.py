"""BaseAPIClient 出站熔断：哪些结果计入下游故障、熔断后本地快速失败。

验收标准（Given-When-Then）：
- 下游持续 5xx → 熔断打开后请求在本地被拒（CircuitOpenError，503），不再发出
- 网络/超时、下游坏压缩体、重定向死循环计入下游故障；调用方本地协议错误（非法 header 等）不计入
- 4xx（含 429）说明下游健康，不触发熔断
- 熔断器名只取 host，不带凭据；畸形 base_url 不在构造期报错
- CircuitOpenError 仍属 APIError 体系，调用方既有的 except APIError 照常生效
"""

from __future__ import annotations

import httpx
import pytest

from infrastructure.external.api_clients.base import (
    APIError,
    BaseAPIClient,
    CircuitOpenError,
    NotFoundError,
    ServerError,
)
from infrastructure.external.circuit_breaker import SREBreaker


def _client(handler) -> tuple[BaseAPIClient, list[httpx.Request]]:
    sent: list[httpx.Request] = []

    def _record(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return handler(request)

    api = BaseAPIClient(
        "https://downstream.test",
        circuit_breaker=SREBreaker("downstream.test", random=lambda: 0.0),
    )
    # 替换内置 RetryTransport：让每次调用恰好对应一次下游请求
    api._client = httpx.AsyncClient(transport=httpx.MockTransport(_record))
    return api, sent


async def _call_n(api: BaseAPIClient, n: int, expected: type[APIError]) -> None:
    for _ in range(n):
        with pytest.raises(expected):
            await api.post("/orders")


@pytest.mark.asyncio
async def test_server_errors_open_the_breaker_and_fail_fast() -> None:
    api, sent = _client(lambda request: httpx.Response(503))

    await _call_n(api, 20, ServerError)
    with pytest.raises(CircuitOpenError) as exc_info:
        await api.post("/orders")

    assert len(sent) == 20, "熔断后的请求不应发到下游"
    assert exc_info.value.status_code == 503
    assert isinstance(exc_info.value, APIError)


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("connection refused"),
        httpx.DecodingError("corrupt gzip body"),  # 下游回了坏的压缩体
        httpx.TooManyRedirects("redirect loop"),  # 下游重定向死循环
    ],
)
@pytest.mark.asyncio
async def test_downstream_httpx_errors_count_as_failures(error: httpx.RequestError) -> None:
    def _fail(request: httpx.Request) -> httpx.Response:
        raise error

    api, sent = _client(_fail)

    await _call_n(api, 20, APIError)
    with pytest.raises(CircuitOpenError):
        await api.post("/orders")
    assert len(sent) == 20


@pytest.mark.asyncio
async def test_client_errors_do_not_open_the_breaker() -> None:
    api, sent = _client(lambda request: httpx.Response(404))

    await _call_n(api, 30, NotFoundError)

    assert len(sent) == 30


@pytest.mark.asyncio
async def test_caller_side_transport_errors_do_not_open_the_breaker() -> None:
    # 非法 header 等请求在本地就构造不出来：是调用方的 bug，不能熔断健康的下游
    def _local_error(request: httpx.Request) -> httpx.Response:
        raise httpx.LocalProtocolError("Illegal header value")

    api, _ = _client(_local_error)
    await _call_n(api, 30, APIError)

    assert api.circuit_breaker._stat.summary() == (30, 30)


@pytest.mark.parametrize(
    ("base_url", "expected_name"),
    [
        ("https://user:secret@api.example.com/v1", "api.example.com"),
        ("user:secret@api.example.com", "api-client"),  # 无 scheme：不把整串（含凭据）当名字
        ("http://host:notaport", "api-client"),  # 畸形 URL：不在构造期报错
    ],
)
def test_breaker_name_never_carries_credentials(base_url: str, expected_name: str) -> None:
    assert BaseAPIClient(base_url).circuit_breaker.name == expected_name
