# API Conventions

This file is the current baseline for reusable REST API behavior in the
`vibejet` foundation library. Module-specific downstream product contracts
should live in downstream application repositories or archived examples, not in
this base library.

## 版本与前缀

- 业务端点统一挂载在 `/api/v1` 前缀下（`backend/main.py` `include_router(..., prefix="/api/v1")`）。
- 健康检查 / metrics 不带 `/api/v1` 前缀（`/health/*`、`/metrics`）。

## 统一响应信封

所有业务响应走统一信封（`backend/core/response.py`）：

```json
{
  "code": 0,
  "message": "Success",
  "data": { "...": "业务数据" },
  "error": null
}
```

- `code`：`shared.codes.BusinessCode`（成功为 `0`）。
- 成功用 `success_response(data, message)`；分页用 `paginated_response(items,total,page,size)` → `data` 为 `{items,total,page,size,pages}`。
- **业务数据始终在 `data` 内**（如 `body.data.user.*`），不要把字段提到顶层。

## 错误响应

错误经全局异常处理器统一渲染（`backend/core/exceptions.py`）：

```json
{
  "code": 30001,
  "message": "...(i18n)",
  "data": null,
  "error": { "type": "...", "message_key": "...", "field": null, "request_id": "...", "locale": "..." }
}
```

- `error` 是对象，不是字符串；判别错误用 `error.message_key` 或 `code`，不要断言 `body.error == "字符串"`。
- 业务码 → HTTP 状态映射（节选）：`UNAUTHORIZED(30001)`→401、`FORBIDDEN(30002)`/`PERMISSION_ERROR(30000)`→403、`INVALID_ACCOUNT(30003)`→401、`NOT_FOUND`→404、`PARAM_VALIDATION_ERROR`→422。
- 401 响应附带 `WWW-Authenticate: Bearer` 头。

## 鉴权

- The current base library does not provide a production authentication module.
- New downstream business endpoints are default-deny: add an explicit actor dependency
  and enforce owner / role / tenant boundaries in the application service.
- Existing scaffold routes (`conversations`, `chat`, `files`, `storage`) are development
  examples unless a downstream project adds authentication and ownership checks.

## 分页 / 幂等

- 分页查询参数：`page`（≥1）、`size`（默认 `DEFAULT_PAGE_SIZE=20`，上限 `MAX_PAGE_SIZE=100`）。
- 幂等：基座提供 `IdempotencyService`（Redis / Noop）。Endpoint-specific
  idempotency semantics belong in that endpoint's API contract.

## 模块索引

There are no current product-specific API modules in this base library.
