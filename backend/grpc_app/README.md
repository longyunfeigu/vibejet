# grpc_app - gRPC 服务骨架

gRPC aio server 骨架，模板本身不携带业务 gRPC 服务，只保留可复用的装配设施。

需要 `grpc` extra：`uv sync --extra grpc`。入口：`backend/grpc_main.py`（`GRPC__ENABLED=true` 时启动）。

## 文件索引

| 文件/目录 | 职责 |
|-----------|------|
| `server.py` | `create_server()`：装配拦截器、TLS、健康检查；业务 service 在标注的扩展点注册 |
| `interceptors/` | request_id / logging / exceptions（业务异常→gRPC status 映射）/ authorization 拦截器 |
| `generated/` | `scripts/gen_protos.sh` 生成的 stub 输出目录（git 跟踪生成结果） |

## 添加业务 service

1. 在 `grpc_app/protos/<pkg>/v1/` 放 `.proto`
2. 运行 `scripts/gen_protos.sh` 生成 stub 到 `generated/`
3. 在 `grpc_app/services/` 实现 servicer
4. 在 `server.py` 的扩展点注册 servicer 并标记健康状态
