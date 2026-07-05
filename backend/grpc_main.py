import asyncio
import signal

from core.config import settings
from core.logging_config import configure_logging
from core.logging_config import get_logger
from grpc_app.server import create_server


logger = get_logger(__name__)


async def main() -> None:
    # Ensure logging configured for gRPC entrypoint
    configure_logging()
    if not settings.grpc.enabled:
        logger.warning("grpc_disabled", message="gRPC disabled by config (GRPC__ENABLED=false)")
        return

    server = await create_server()
    address = f"{settings.grpc.host}:{settings.grpc.port}"
    logger.info("grpc_starting", address=address)
    await server.start()
    logger.info("grpc_started", address=address)

    # SIGTERM（docker stop / 编排器）与 SIGINT 都要优雅排水，
    # 否则在途 RPC 被直接掐断
    stop_requested = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_requested.set)

    stop_waiter = asyncio.ensure_future(stop_requested.wait())
    termination_waiter = asyncio.ensure_future(server.wait_for_termination())
    try:
        # 信号或服务器自行终止，先到先响应（SIGINT/SIGTERM 均已由
        # add_signal_handler 转为 stop_requested 事件）
        await asyncio.wait(
            {stop_waiter, termination_waiter}, return_when=asyncio.FIRST_COMPLETED
        )
    finally:
        stop_waiter.cancel()
        termination_waiter.cancel()
        logger.info("grpc_stopping", grace_seconds=settings.grpc.shutdown_grace_seconds)
        await server.stop(grace=settings.grpc.shutdown_grace_seconds)
        logger.info("grpc_stopped")


if __name__ == "__main__":
    asyncio.run(main())
