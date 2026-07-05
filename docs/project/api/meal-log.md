# Meal Log API

随手食记 meal 模块公共接口（introduced by Epic 1 拍照记录一餐，契约状态：planned——实现偏离时回写本文件）。
端点位于 `/api/v1`，router 级 Bearer 认证，统一业务信封与 owner-scoped 归属约定见 [conventions.md](conventions.md)。

**归属**：全部 meal 资源 owner-scoped——创建写 `owner_id=当前用户`；越权访问 → `NOT_FOUND` / 404（与不存在同响应）。

## 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/meal-photos` | 上传餐食照片（multipart；仅 image/*；≤10MB；非空）。薄端点委托 file_asset（kind=meal-photo），返回 `data.photo_id`（即 file asset id） |
| POST | `/api/v1/meal-recognitions` | 发起识别；body `{photo_id}` 或 `{text}` 二选一（text ≤200 字）。同步等待 ≤10s，返回 `data.{status, reason?, items[]}` |
| POST | `/api/v1/meal-records` | 保存饮食记录；需 `Idempotency-Key` 头；body `{photo_id?, source(photo\|text), meal_type, items[]}`（items 非空）。201 返回 `data.record_id` |

## 识别响应形状

```json
{ "status": "ready | unrecognized", "reason": "仅 unrecognized 时给出",
  "items": [{ "name": "…", "portion": 1.0, "calories": 0, "protein": 0, "fat": 0, "carbs": 0 }] }
```

- `status=unrecognized`（低置信度/非食物）是 200 业务态，不是错误。
- 识别调用**零副作用**：不产生任何 meal_records 行。

## 错误语义

| 场景 | HTTP | code / message_key |
|------|------|--------------------|
| AI 服务超时（>10s）/ 5xx / 网络失败 | 503 | `AI_UNAVAILABLE`（本模块新增业务码）；照片保留可重试 |
| photo_id 非本人 / 不存在 | 404 | `NOT_FOUND`（同响应） |
| 参数非法（空文件/超限/非图片/items 空/text 超长/photo_id 与 text 同给或同缺） | 422 | `PARAM_VALIDATION_ERROR` |
| 无凭证 | 401 | `UNAUTHORIZED` |

## 幂等

`POST /api/v1/meal-records` 按 `(owner, Idempotency-Key)` 幂等（复用基座 `IdempotencyService`，同 presign-upload 模式）：重复 key 返回首次 201 结果；DB 写失败时 key 不落缓存（可重试）。key 由前端每次进入确认区生成，重试沿用、重新确认换新。
