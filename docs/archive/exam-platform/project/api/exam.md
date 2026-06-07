# API · exam 模块

> 范围：业务资料录入、考试目标创建、AI 知识点提取与确认（Epic 2）。
> 全局约定见 [conventions.md](./conventions.md)。数据模型见 [../data/exam.md](../data/exam.md)。
> 响应体均为统一信封，下表「Response」列描述 `data` 内结构。

## 权限

全部端点 `Depends(require_admin)`（role=admin → 放行；非 admin → 403 FORBIDDEN；无会话 → 401 UNAUTHORIZED）。

---

## 业务资料（Materials）

### POST /api/v1/exam/materials

录入业务资料：粘贴文本或上传 txt/md 文件。

- **Request（JSON）**：`{ "content": "<文本内容>" }`
- **Request（multipart）**：`file=<.txt or .md or .pdf>`（API 层读取内容，pdf 用 pypdf 提取文字，不使用对象存储）
- **副作用**：录入时全文经 `split_into_chunks` 切块持久化到 `material_chunks`（供知识点提取 map-reduce 与 grounded 出题共用；对调用方透明）
- **Response 201**（`data`）：`{ "id": int, "content": str, "filename": str|null, "status": "ready", "created_by": int, "created_at": str }`
- **错误**：
  - 空内容（无文本且无文件）→ **422** `error.message_key="param.validation_error"`
  - 不支持的文件格式（非 .txt/.md）→ **422** `error.message_key="unsupported_format"`

### GET /api/v1/exam/materials

获取业务资料列表（供管理员查看与 Epic 3 选择资料）。按创建时间倒序（最新在前）。列表项不返回全文，只返回截断预览。

- **Response 200**（`data`）：`{ "items": [{"id": int, "content_preview": str(≤100字), "filename": str|null, "status": str, "extraction_status": str|null, "created_at": str}] }`

### GET /api/v1/exam/materials/{id}

获取业务资料详情（供下游出题环节读取）。

- **Response 200**（`data`）：`{ "id", "content", "filename", "status", "created_by", "created_at" }`
- **错误**：id 不存在 → **404** `error.message_key="material.not_found"`

---

## 考试目标（Exam Objectives）

### GET /api/v1/exam/objectives

获取考试目标列表（供管理员查看和 Epic 3 选择目标）。

- **Response 200**（`data`）：`{ "items": [{"id": int, 六字段, "created_by": int}] }`

### POST /api/v1/exam/objectives

创建考试目标（六字段结构化表单）。

- **Request**：
  ```json
  {
    "target_object": "str（必填）考核对象",
    "purpose": "str（必填）考核目的",
    "knowledge_points_scope": "str（必填）覆盖知识点",
    "question_type_difficulty_score": "str（必填）题型/难度/分值要求",
    "out_of_scope": "str（可选，nullable）不考核范围",
    "subjective_scoring_focus": "str（必填）主观题评分重点"
  }
  ```
- **Response 201**（`data`）：`{ "id": int, 六字段, "created_by": int, "created_at": str }`
- **错误**：缺任一必填字段 → **422** `error.field=<缺项字段名>` + `error.details.errors`（完整校验错误列表）

### GET /api/v1/exam/objectives/{id}

获取考试目标（供 Epic 3 出题约束、Epic 5 评分重点读取）。

- **Response 200**（`data`）：`{ "id", 六字段, "created_by" }`
- **错误**：id 不存在 → **404** `error.message_key="objective.not_found"`

---

## 知识点（Knowledge Points）

所有知识点端点均在 `/api/v1/exam/materials/{material_id}/knowledge-points` 下。

### POST /api/v1/exam/materials/{material_id}/knowledge-points

触发 AI 从指定资料中**异步**提取知识点（FastAPI BackgroundTasks，map-reduce over `material_chunks`）。立即返回 202，前端轮询 GET 获取结果。

- **Request**：无（仅路径参数 `material_id`）
- **Response 202**（`data`）：`{ "task_id": null, "extraction_status": "processing" }`（BackgroundTasks 无 task_id，恒为 null）
- **幂等**：material 已 `processing` 时不重复调度后台任务（仍返回 202 + processing）
- **前端轮询**：每 2s 调用 GET，检查 `extraction_status`；'completed'/'failed' 停止轮询；超过 60s 视为超时展示失败 UI（可重新触发；进程重启会丢失后台任务，靠超时+重试兜底）
- **错误**：material_id 不存在 → **404** `error.message_key="material.not_found"`

### PUT /api/v1/exam/materials/{material_id}/knowledge-points

全量替换并确认知识点（编辑/删除/新增后统一提交）。

- **Request**：`{ "items": [{"name": str}, ...] }`（空数组合法，表示清空已确认知识点）
- **Response 200**（`data`）：`{ "items": [{"id": int, "name": str, "confirmed": true}] }`
- **语义**：幂等；删除该 material 全部既有 KP → 插入提交项，全部 `confirmed=true`（见 D4）
- **错误**：material_id 不存在 → **404**

### GET /api/v1/exam/materials/{material_id}/knowledge-points

获取知识点列表及提取状态（前端轮询此端点），支持 `?confirmed=true|false` 过滤。

- **Query params**：`confirmed`（可选；不传则返回全部）
- **Response 200**（`data`）：`{ "extraction_status": "processing"|"completed"|"failed"|null, "items": [{"id": int, "name": str, "confirmed": bool}] }`
- Epic 3 / Epic 6 调用：`?confirmed=true`（仅获取已确认知识点）

---

## 错误码（本模块新增）

| 码 | 名称 | HTTP | message_key |
|----|------|------|-------------|
| 20005 | `MATERIAL_NOT_FOUND` | 404 | `material.not_found` |
| 20006 | `OBJECTIVE_NOT_FOUND` | 404 | `objective.not_found` |

复用：`PARAM_VALIDATION_ERROR`(10003/422)、`UNAUTHORIZED`(30001/401)、`FORBIDDEN`(30002/403)。
