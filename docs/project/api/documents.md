# Documents API

文档解析模块公共接口。所有端点位于 `/api/v1/documents`，要求 Bearer 认证，
返回统一业务信封 `Response[T]`（见 `docs/project/api/conventions.md`）。

异步模型：创建/重解析立即返回，解析在后台执行；客户端轮询详情接口直到
`status` 变为 `ready` 或 `failed`，再从 content 端点取 Markdown。

## 状态机

`pending → parsing → ready | failed`；`ready`/`failed` 可通过 reparse 回到 `pending`。

## 端点

### POST /api/v1/documents

从已上传的文件资产创建文档并触发解析。

请求体：

```json
{ "file_asset_id": 123, "title": "可选标题，默认取原始文件名" }
```

响应 `data`: `DocumentDTO`（status 为 `pending`，解析随即开始）。
文件资产不存在或已删除 → 业务码 `NOT_FOUND (20004)`。

### GET /api/v1/documents

分页列表。Query：`page`、`size`、`status`（pending/parsing/ready/failed）、`file_asset_id`。

### GET /api/v1/documents/{id}

文档详情（状态轮询用）。`DocumentDTO` 字段：

| 字段 | 说明 |
|------|------|
| `status` | pending / parsing / ready / failed |
| `parser` | 完成（或失败）时所用解析器：markitdown / textin |
| `error_code` | failed 时的稳定错误码，如 `document.parse.empty_content` |
| `error_message` | failed 时的错误详情 |
| `metadata` | 解析元数据（chars、pages 等） |

不存在 → `DOCUMENT_NOT_FOUND (60020)`。

### GET /api/v1/documents/{id}/content

获取解析产物：`{ id, status, parser, markdown }`。
非 ready 状态 → `DOCUMENT_NOT_READY (60021)`。

### POST /api/v1/documents/{id}/reparse

重置为 pending 并重新调度解析。`parsing` 中调用 → `DOCUMENT_ALREADY_PROCESSING (60022)`；
但 `parsing` 超过 `DOCUMENT__PARSING_STALE_SECONDS`（默认 900s）视为孤儿任务
（如进程重启丢失后台任务），允许强制重置恢复。

### DELETE /api/v1/documents/{id}

软删除。响应 `data`: `{ "deleted": true, "status": "..." }`。

## 错误码

| 业务码 | 含义 |
|--------|------|
| 60020 `DOCUMENT_NOT_FOUND` | 文档不存在 |
| 60021 `DOCUMENT_NOT_READY` | 解析未完成，content 不可用 |
| 60022 `DOCUMENT_ALREADY_PROCESSING` | 解析进行中，拒绝并发操作 |

`error_code` 字段（区别于业务码，描述解析失败原因）：

| error_code | 含义 |
|------------|------|
| `document.parse.empty_content` | 未提取到有效文本（markitdown 遇扫描件的典型结果） |
| `document.parse.unsupported_format` | 解析器不支持的格式 |
| `document.parse.too_large` | 超过 `DOCUMENT__MAX_PARSE_BYTES` |
| `document.parse.file_asset_missing` | 建档后文件资产被删除 |
| `document.parse.textin_error` / `textin_timeout` / `textin_http_error` / `textin_network_error` | TextIn 调用失败（details 含 TextIn 原始码） |
| `document.parse.internal_error` | 未预期异常兜底 |

## 配置

| 环境变量 | 默认 | 说明 |
|----------|------|------|
| `DOCUMENT__PARSER` | `markitdown` | 解析器二选一：markitdown / textin，不混用不降级 |
| `DOCUMENT__MAX_PARSE_BYTES` | 50MB | 单文件解析输入上限 |
| `DOCUMENT__PARSING_STALE_SECONDS` | 900 | parsing 超时视为孤儿任务，允许 reparse 强制恢复 |
| `DOCUMENT__TEXTIN_APP_ID` / `DOCUMENT__TEXTIN_SECRET_CODE` | - | parser=textin 时必填（缺失则启动失败） |
| `DOCUMENT__TEXTIN_BASE_URL` | `https://api.textin.com` | TextIn 端点 |
| `DOCUMENT__TEXTIN_TIMEOUT` | 120 | TextIn 请求超时（秒） |

markitdown 依赖 optional extra：`uv sync --extra documents`。

## 已知留白（与 files 模块一致）

- 列表不做 owner 过滤、详情不做 ownership 校验 —— 下游项目需补 actor/ownership 检查
- BackgroundTasks 为进程内执行：进程重启会令文档停留在 `parsing`，超过
  `DOCUMENT__PARSING_STALE_SECONDS` 后可用 reparse 端点恢复；
  多副本部署应将 `process_document` 迁移到 Celery（service 方法可直接复用）
