# API 约定（全局）

> 全局 API 约定 + 模块索引。各模块端点契约见 `docs/project/api/{module}.md`。
> 本文件仅在**全局约定**变化时修改；模块端点变化只改对应模块文件。

## 版本与前缀

- 业务端点统一挂载在 `/api/v1` 前缀下（`backend/main.py` `include_router(..., prefix="/api/v1")`）。
- 下游考试平台端点使用 `/api/v1/exam/...` 业务域前缀。
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

- 会话机制：**服务端 `sessions` 表 + HttpOnly Cookie**（不透明 token）。前端请求需 `withCredentials`。
- 受保护端点统一依赖 `get_current_user`（无有效会话 → 401）；角色门用 `require_role` / `require_admin` / `require_employee`（不匹配 → 403）。详见 `identity.md`。
- 既有基座路由（conversations/chat/files/storage）当前不要求鉴权（基座 scaffold 基线）。

## 分页 / 幂等

- 分页查询参数：`page`（≥1）、`size`（默认 `DEFAULT_PAGE_SIZE=20`，上限 `MAX_PAGE_SIZE=100`）。
- 幂等：基座提供 `IdempotencyService`（Redis / Noop）；登录等写操作的幂等语义见对应模块文档。

## 模块索引

| 模块 | 文件 | 范围 |
|------|------|------|
| identity | [identity.md](./identity.md) | 模拟登录、会话、身份、角色访问控制（Epic 1） |
| exam | [exam.md](./exam.md) | 业务资料录入、考试目标、AI 知识点提取与确认（Epic 2） |
| question | [question.md](./question.md) | AI 结构化出题、题目审核与确认（Epic 3） |
| exam-taking | [exam-taking.md](./exam-taking.md) | 组卷与分配试卷、员工作答与一次性提交（幂等）（Epic 4） |
| grading | [grading.md](./grading.md) | 客观自动判分、主观题 AI 评分③、人工复核改终分（Epic 5） |
