"""The real gRPC server (create_server + all interceptors) answers the standard health check."""

from __future__ import annotations

import socket

import pytest

grpc = pytest.importorskip("grpc")
health_pb2 = pytest.importorskip("grpc_health.v1.health_pb2")
health_pb2_grpc = pytest.importorskip("grpc_health.v1.health_pb2_grpc")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


async def test_health_check_reports_serving(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.config import settings
    from grpc_app.server import create_server

    port = _free_port()
    monkeypatch.setattr(settings.grpc, "host", "127.0.0.1")
    monkeypatch.setattr(settings.grpc, "port", port)
    monkeypatch.setattr(settings.grpc.tls, "enabled", False)

    server = await create_server()
    await server.start()
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            reply = await health_pb2_grpc.HealthStub(channel).Check(
                health_pb2.HealthCheckRequest(), timeout=5
            )
    finally:
        await server.stop(grace=None)

    assert reply.status == health_pb2.HealthCheckResponse.SERVING
