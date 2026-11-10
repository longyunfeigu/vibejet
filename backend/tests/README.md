# backend/tests — 后端测试

pytest + pytest-asyncio；从 `backend/` 目录运行：`uv run pytest tests/ -v`。
`conftest.py` 在采集前兜底设置必需环境变量（SECRET_KEY 等）。
仓储类测试统一用内存 SQLite（aiosqlite + StaticPool）；服务类测试用 fake UoW/端口，不触网。

## 文件索引

| 文件 | 覆盖内容 |
|------|---------|
| `conftest.py` | pytest bootstrap：强制环境变量兜底 |
| `test_settings_config.py` | Settings 校验：别名、未知键 fail-fast、SECRET_KEY 弱值/长度、DEBUG 默认与生产互斥 |
| `test_base_entity.py` | 领域基础实体行为 |
| `test_base_repository.py` | 泛型仓储基类 + 软删过滤 |
| `test_unit_of_work.py` | UoW 事务语义：干净退出自动 commit、异常回滚、中途 commit 后续写入仍落库、readonly 写保护 |
| `test_agent_config_repository.py` | AgentConfig 唯一名冲突（create/改名撞唯一索引 → 域异常 409） |
| `test_user_oauth_repository.py` | 用户仓储 OAuth 联合身份与 (provider,sub) 唯一性 |
| `test_auth_google_service.py` / `test_auth_lark_service.py` | Google / 飞书登录应用服务 |
| `test_google_code_exchanger.py` / `test_lark_code_exchanger.py` | OAuth 授权码换 token 客户端 |
| `test_chat_service_stream.py` | SSE 流式聊天：预校验先于流（4xx 时机）+ 完整事件序列；非流式 LLM 失败不外泄上游报错原文 |
| `test_i18n_message_keys.py` | 翻译表校验接进 pytest（调 `scripts/validate_po.py`：语法、代码用到的 key 都有非空译文）+ 业务异常缺翻译时退回默认文案、不返回 key |
| `test_http_logging_middleware.py` | HTTP 日志中间件（纯 ASGI）的特征测试：请求/响应日志、耗时头、请求体记录与脱敏（DEBUG 开关）、异常路径；含一条走真实 FastAPI 栈的用例 |
| `test_tracing_instrument_app.py` | `instrument_app` 的特征测试：四类插桩各自成功/失败/缺依赖，用假模块替换 OpenTelemetry 插桩器 |
| `test_grpc_interceptors.py` | gRPC 日志与异常映射拦截器的特征测试：业务异常/系统异常/已上报状态的映射与日志；含一条进程内真实 grpc.aio 服务端的用例 |
| `test_aiokafka_consumer_start.py` | `AiokafkaConsumer.start` 的特征测试：启停/建连/TLS、反序列化失败转 DLQ、中间件、重试分层与 DLQ、提交与位点、延迟重投、再均衡监听、告警日志（需 aiokafka extra） |
| `test_kafka_driver_config.py` | Kafka 单驱动配置链路：默认 aiokafka；`KAFKA__DRIVER=confluent` 启动即失败并提示迁移；builder/factory 只产出 aiokafka 客户端 |
| `test_aiokafka_publisher.py` | `AiokafkaPublisher` 单测：参数映射到真实 aiokafka（`max_batch_size`、幂等要求 acks=all）、zstd 编解码可用、`publish_many` 先全部发送再统一等待 |
| `test_aiokafka_offsets.py` | 位点批量提交（`OffsetTracker`）：按条数/间隔触发、收回分区时剔除、提交失败保留待下批重试 |
| `test_kafka_integration.py` | aiokafka 真实 broker 集成测试（设 `KAFKA_INTEGRATION_BOOTSTRAP` 才跑，否则 skip；CI 的 kafka-integration job 起 apache/kafka:3.9.1）：发布消费、延迟重投只暂停所在分区、DLQ、转投被 broker 拒收时不越过该记录并退避重试、收回分区时冲刷位点、事务性重投、批量提交重启不丢、跨线程停止 |
| `test_s3_provider_upload.py` | `S3Provider.upload` 的特征测试：假 boto3 客户端下的上传参数（ACL/元数据/类型）、ETag 与本地 MD5 回退、SDK 错误映射 |
| `test_storage_middleware_upload.py` | `MiddlewareStorage.upload` 的特征测试：before/after/on_error 钩子的顺序、失败时逐个通知、异常原样抛出 |
| `test_redis_client_lock.py` | `RedisClient.lock` 的特征测试：获取/超时/自动续期/释放失败，用假的异步 redis 锁 |
| `test_api_client_request.py` | `BaseAPIClient._request` 的特征测试：重试、限流/认证/404 等错误映射、请求头合并、响应包装（httpx.MockTransport） |
| `test_document_entity.py` / `test_document_repository.py` / `test_document_service.py` | 文档模块状态机、仓储、解析编排 |
| `test_document_parsers.py` | 文档解析器（需 documents extra，未装则 skip） |
| `test_file_asset_relay_cleanup.py` | relay 上传 DB 失败时孤儿对象 best-effort 清理 |
| `test_storage_upload_stream_abort.py` | 流式上传中断时 multipart abort 补偿 |
| `test_idempotency_presign.py` | presign 幂等（Idempotency-Key） |
| `test_observability_fallback.py` | 可观测性降级路径 |
