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

## 鉴权与归属

- 登录：JWT Bearer（`backend/api/dependencies.py` 的 `get_current_user` → `UserDTO(id, is_superuser, ...)`），
  业务路由统一挂 router 级认证闸门；未认证 → `UNAUTHORIZED (30001)` / 401。
- **Ownership（default-deny，已强制）**：conversations / chat / files / storage / documents 的资源端点
  只作用于当前用户的资源——创建时写 `owner_id=当前用户`；列表强制 owner 过滤（无"查看全部"参数）；
  详情/变更在 application service 里加载后用领域方法 `belongs_to(owner_id)` 断言。
- **越权响应 = 404**：非 owner 访问与资源不存在同响应（同业务码、同 message_key），不泄露资源存在性。
  `owner_id` 为 NULL 的遗留行视为孤儿，对所有用户不可见。superuser 无越权通道（未来 RBAC epic 再设计）。
- **模式约定**：route-facing 服务方法的 `owner_id` 是**必填**关键字参数（fail-closed，漏传即 TypeError）；
  路由只负责传 `current_user.id`；后台 worker/清理任务不经过归属断言（无"当前用户"语义）。
  下游新增业务端点照此模式实现。
- **已知例外**：`/agent-configs` 是共享配置资源，无 owner 语义，目前任何登录用户可读写；
  多用户产品接入前需按产品需求补角色/租户边界（Epic-1 decisions.md D5）。

## 分页 / 幂等

- 分页查询参数：`page`（≥1）、`size`（默认 `DEFAULT_PAGE_SIZE=20`，上限 `MAX_PAGE_SIZE=100`）。
- 幂等：基座提供 `IdempotencyService`（Redis / Noop）。Endpoint-specific
  idempotency semantics belong in that endpoint's API contract.

## 模块索引

- [auth.md](auth.md) — 注册 / 登录 / 当前用户 / OAuth
- [conversations.md](conversations.md) — 会话 CRUD、消息/Run 查询、chat（SSE）
- [documents.md](documents.md) — 文档创建 / 解析 / 内容获取
- [files.md](files.md) — 文件列表 / 详情 / 签名 URL / 删除、storage 上传与确认
