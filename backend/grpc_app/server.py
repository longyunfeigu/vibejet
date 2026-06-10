# input: core.config.settings.grpc, grpc_app 拦截器, grpc 健康检查服务
# output: create_server() gRPC aio server 工厂（含拦截器/TLS/健康检查）
# owner: wanhua.gu
# pos: gRPC 服务 - server 骨架装配；业务 service 在此注册；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""gRPC aio server skeleton.

This template ships no business gRPC service. To add one:
1. Put your `.proto` under `grpc_app/protos/<pkg>/` and run `scripts/gen_protos.sh`
2. Implement the servicer under `grpc_app/services/`
3. Register it below in `create_server()` (see the marked extension point)
"""

from __future__ import annotations

import os
import sys
from typing import Sequence

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from core.config import settings
from core.logging_config import get_logger
from grpc_app.interceptors.exceptions import ExceptionMappingInterceptor
from grpc_app.interceptors.logging import LoggingInterceptor
from grpc_app.interceptors.request_id import RequestIdInterceptor

# Make `grpc_app/generated` importable as a top-level root so generated stubs
# (which import sibling packages absolutely) resolve correctly.
_gen_root = os.path.join(os.path.dirname(__file__), "generated")
if _gen_root not in sys.path:
    sys.path.insert(0, _gen_root)

logger = get_logger(__name__)


async def create_server() -> grpc.aio.Server:
    interceptors: Sequence[grpc.aio.ServerInterceptor] = (
        RequestIdInterceptor(),
        LoggingInterceptor(),
        ExceptionMappingInterceptor(),  # maps business exceptions
    )

    options = [
        ("grpc.max_concurrent_streams", max(1, settings.grpc.max_concurrent_streams)),
    ]
    server = grpc.aio.server(interceptors=interceptors, options=options)

    # --- Extension point: register business services here ---------------
    # from grpc_app.generated.<pkg> import <svc>_pb2_grpc
    # from grpc_app.services.<svc>_service import <Svc>Service
    # <svc>_pb2_grpc.add_<Svc>ServiceServicer_to_server(<Svc>Service(), server)
    # health_svc.set("<pkg>.<Svc>Service", health_pb2.HealthCheckResponse.SERVING)
    # ---------------------------------------------------------------------

    # Health service
    health_svc = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_svc, server)
    health_svc.set("", health_pb2.HealthCheckResponse.SERVING)

    # Bind address
    address = f"{settings.grpc.host}:{settings.grpc.port}"

    if settings.grpc.tls.enabled:
        if not (settings.grpc.tls.cert and settings.grpc.tls.key):
            raise RuntimeError("GRPC TLS enabled but cert/key not provided")
        with open(settings.grpc.tls.cert, "rb") as f:
            cert_chain = f.read()
        with open(settings.grpc.tls.key, "rb") as f:
            private_key = f.read()
        root_certificates = None
        if settings.grpc.tls.ca:
            with open(settings.grpc.tls.ca, "rb") as f:
                root_certificates = f.read()
        creds = grpc.ssl_server_credentials(
            [(private_key, cert_chain)],
            root_certificates=root_certificates,
            require_client_auth=bool(root_certificates),
        )
        server.add_secure_port(address, creds)
    else:
        server.add_insecure_port(address)

    return server
