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
| `test_agent_config_repository.py` | AgentConfig 唯一名冲突（create/改名撞唯一索引 → 域异常 409） |
| `test_user_oauth_repository.py` | 用户仓储 OAuth 联合身份与 (provider,sub) 唯一性 |
| `test_auth_google_service.py` / `test_auth_lark_service.py` | Google / 飞书登录应用服务 |
| `test_google_code_exchanger.py` / `test_lark_code_exchanger.py` | OAuth 授权码换 token 客户端 |
| `test_chat_service_stream.py` | SSE 流式聊天：预校验先于流（4xx 时机）+ 完整事件序列 |
| `test_document_entity.py` / `test_document_repository.py` / `test_document_service.py` | 文档模块状态机、仓储、解析编排 |
| `test_document_parsers.py` | 文档解析器（需 documents extra，未装则 skip） |
| `test_file_asset_relay_cleanup.py` | relay 上传 DB 失败时孤儿对象 best-effort 清理 |
| `test_storage_upload_stream_abort.py` | 流式上传中断时 multipart abort 补偿 |
| `test_idempotency_presign.py` | presign 幂等（Idempotency-Key） |
| `test_observability_fallback.py` | 可观测性降级路径 |
