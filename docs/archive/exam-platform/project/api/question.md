# API · question 模块

> 范围:AI 结构化出题、题目审核与确认（Epic 3）。
> 全局约定见 [conventions.md](./conventions.md)。数据模型见 [../data/question.md](../data/question.md)。
> 响应体均为统一信封，下表「Response」列描述 `data` 内结构。
> 全部端点 `Depends(require_admin)`（仅出题管理员；见 [identity.md](./identity.md)）。

## 端点

### POST /api/v1/exam/questions/generate

AI 基于考试目标和资料**原文片段**生成一组结构化题目，落为「待审核」题集。

- **Auth**：`require_admin`。
- **Request**：`{ "objective_id": int, "material_id": int, "knowledge_point_names"?: [str] }`
  - `knowledge_point_names`（可选）：勾选的知识点子集，把出题覆盖面收窄到所选点。**省略或空数组 = 用该资料全部已确认 KP**（向后兼容）；非空 → 与已确认 KP **取交集**（保持已确认顺序），非交集名忽略；非空但交集为空（勾选名全非法）→ `status="invalid"` + reasons，不调 LLM、不落库。
- **grounding**：按所选/已确认 KP 名字面匹配选相关 `material_chunks`（保序去重，上限 12；无命中回退前 N；无 chunk 降级）作为出题原文依据；每题产出 `source_quote`（逐字摘自所喂原文片段）。传子集时 grounding 锚定来源同步收窄到所选 KP。
- **Response 200**（`data`）：`{ "set_id": int, "questions": [Question], "status": "generated" | "invalid", "reasons": [str] }`
  - 成功：`status="generated"`，题集落库 `status=pending_review`，每题持久化 `source_quote`。
  - **内容不合格也返回 200**（不是错误信封）：三道闸任一不过 → `status="invalid"` + `reasons[]`：① 形状闸（非法 JSON/类型）② domain 闸（字段不全/题量不足/无主观题）③ **忠实闸**（某题 `source_quote` 不在所喂原文片段内，疑似脱离资料编造）。前端提示重试或人工补足（R3.4）。
- **基础设施异常**（LLM timeout / 连接失败 / 鉴权失效 / 限流）：走错误信封 **503** `QUESTION_GENERATION_UNAVAILABLE`，不混进 `invalid`——让监控可观测、前端区分"系统故障 vs 内容要补"。
- **超时预算**：出题这条 LLM 调用单独设 `timeout < 60s` 且 `max_retries=0或1`（避免叠加重试撞 NFR P95<60s）。
- **幂等**：每次调用生成一个新题集，不复用。

### GET /api/v1/exam/questions

按题集列出题目，供审核和下游组卷读取。

- **Auth**：`require_admin`。
- **Request**：query `set_id: int`（+ 分页 `page`/`size`）
- **Response 200**（`data`，分页信封）：`{ "items": [Question], "total", "page", "size", "pages" }`

### PUT /api/v1/exam/questions/{id}

编辑一道题（题集须仍为 `pending_review`）。

- **Auth**：`require_admin`。
- **Request**：`{ "stem"?, "options"?, "reference_answer"?, "scoring_points"?, "score"?, "type"?, "knowledge_point_names"?: [str] }`
- **Response 200**（`data`）：`{ "question": Question }`
- **错误**：题不存在 → **404** `QUESTION_NOT_FOUND`。

### DELETE /api/v1/exam/questions/{id}

软删一道题。

- **Auth**：`require_admin`。
- **Response 200**（`data`）：`{ "deleted": true }`
- **错误**：题不存在 → **404** `QUESTION_NOT_FOUND`。

### POST /api/v1/exam/questions

人工新增一道题，纳入题集并参与达标校验（R3.3）。

- **Auth**：`require_admin`。
- **Request**：`{ "set_id": int, "type", "stem", "options"?, "reference_answer"?, "scoring_points"?, "score", "knowledge_point_names"?: [str] }`
- **Response 201**（`data`）：`{ "question": Question }`，`source="manual"`。

### POST /api/v1/exam/questions/confirm

确认题集。确认前强制跑达标校验，达标才推 `confirmed`。

- **Auth**：`require_admin`。
- **Request**：`{ "set_id": int }`
- **Response 200**（`data`）：`{ "set_id": int, "status": "confirmed" }`
  - 幂等：对已确认题集再次确认，返回 `confirmed`，不报错。
- **错误**：题集不达标（题数<5 / 题型<2 / 无主观）→ **422** `QUESTION_SET_BELOW_MINIMUMS`，`error` 内说明缺什么（R3.2 enforcement）。题集不存在 → **404** `QUESTION_SET_NOT_FOUND`。

## Question 结构（响应 `data` 内）

```json
{
  "id": int,
  "set_id": int,
  "type": "single_choice" | "true_false" | "short_answer",
  "stem": "题干",
  "options": ["A...", "B..."],          // 客观题用；简答为 null
  "reference_answer": "参考答案",         // 客观题
  "scoring_points": ["评分要点1", ...],   // 主观题
  "score": int,
  "source": "ai_generated" | "manual",
  "knowledge_point_names": [str],        // 关联知识点名快照（D2=A，不存 epic-2 外键）
  "source_quote": str | null             // grounding 锚点：依据的逐字原文片段；name-only 降级或人工题为 null
}
```

## 错误码（本模块新增）

> 码值挂 6xxxx（AI 段）；实现时与 `backend/shared/codes/` 现有占用核对，下面是建议值。

| 码（建议） | 名称 | HTTP | 触发 |
|----------|------|------|------|
| 60020 | `QUESTION_SET_NOT_FOUND` | 404 | `set_id` 不存在 |
| 60021 | `QUESTION_NOT_FOUND` | 404 | 编辑/删除不存在的题 |
| 60022 | `QUESTION_SET_BELOW_MINIMUMS` | 422 | 确认时题集不达标 |
| 60023 | `QUESTION_GENERATION_UNAVAILABLE` | 503 | 出题时 LLM 基础设施异常（timeout/连接/鉴权/限流） |

- generate 的「内容不合格」（字段不全/题量不足/无主观/非法 JSON）**不走错误信封**，按 `200 + data.status='invalid' + data.reasons[]` 返回（R3.4）；「基础设施异常」走 `503`。
- 复用：`UNAUTHORIZED`(401)、`FORBIDDEN`(403，非 admin)。

## 待对齐

- `identity.md` 预告过路径 `/exam/admin/questions`，与 Story 3.1/3.2 `验证:` 命令的 `/exam/questions` 不一致。本模块按 Story AC 走 `/exam/questions`；建议把 identity.md 那条括号举例对齐。
