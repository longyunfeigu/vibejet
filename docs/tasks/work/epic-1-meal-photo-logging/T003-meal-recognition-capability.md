# T003 识别能力（photo + text）

**Epic:** [Epic 1 拍照记录一餐](../../epics/epic-1-meal-photo-logging/epic.md) · **Unit / Scope:** U2 Story 1.2（后端全部）+ U5 Story 1.5（后端识别通道；partial） · **Depends:** T001 · **Wave:** 2

**Generated from:** Review Pack `docs/tasks/plans/2026-07-05-epic-1-meal-photo-logging/` · Unit `U2`+`U5(partial)` · Story `1.2`/`1.5` · Design anchors `design.md#api-delta` `design.md#must-hold` · Decision anchors `decisions.md#D1 #D3 #D6 #D7` · Catalog anchors `docs/project/api/meal-log.md`
**Task scope:** 本文档是执行投影。本 task 交付识别后端能力（photo+text 同端点，D6）；U2 done 还需 T005 FE AC，U5 done 还需 T004 的记录同构测试 + T005 FE。本 task 含公共 `LLMPort` 契约扩展（D7，strict 面）。

## 1. Context
### Source anchors
- Review Pack: design.md 合同区 API Delta 识别行为决策表 + Must Hold（本 task 的行为规范；状态机全图在附录）+ decisions.md D1/D3/D6/D7 完整论证
- Task Index: Wave 2；`application/ports/llm.py` + `infrastructure/external/llm/*` 本 task 独占
- Story AC: `stories/us002-ai-recognition.md` + `stories/us005-text-fallback-entry.md`
### 现状
- `LLMPort` 无图像 block（ContentBlock 仅 Text/ToolUse/ToolResult）；有 `json_schema` 结构化输出；anthropic/openai 两 provider
- T001 已建 `api/routes/meal_recognitions.py` 骨架
### 目标态
- `ImageBlock` 进入 LLMPort content 模型，两 provider 支持；`meal_recognition_service` 编排 photo/text → 结构化明细，超时/失败按 §4 decision table 翻译业务态；新增业务码 `AI_UNAVAILABLE`
### 继承假设
- A1 (D7): ImageBlock 用 base64 source；anthropic `source.data` / openai `image_url` 编码差异在各 provider 内消化
- A2 (D3): 同步等待，超时 10s（可配置），不引入队列
### Read first
- `backend/application/ports/llm.py` - 现有 content 模型与 json_schema 输出（扩展目标）
- `backend/infrastructure/external/llm/anthropic_provider.py` - provider 序列化模式
- `backend/infrastructure/external/llm/openai_provider.py` - 同上
- `backend/shared/codes/__init__.py` - 业务码注册点（AI_UNAVAILABLE 新增）
- `backend/application/services/document_service.py` - 外部调用失败翻译成业务错误的既有模式
### Write scope
- May modify: <!-- vj-plan-review: applied [coherence/3] -->
  - `backend/application/ports/llm.py`
  - `backend/infrastructure/external/llm/`（两 provider + 共享）
  - `backend/application/services/meal_recognition_service.py`
  - `backend/api/routes/meal_recognitions.py`
  - `backend/shared/codes/__init__.py`
  - `backend/shared/prompts/`（识别 prompt，新建目录）
  - `backend/tests/test_meal_recognition.py`
  - `backend/tests/test_llm_*.py`（ImageBlock 用例追加）
- Do not modify: `meal_records` 相关任何文件（识别零副作用不变量）、`backend/main.py`

## 2. Implementation Plan
### Phase 0: 廉价验证闸（先验证 D1 假设，再动公共端口）<!-- vj-plan-review: applied [adversarial/3] -->
- [ ] 用 5-10 张真实餐食照片 + MEAL_SCHEMA prompt 直连候选模型 spike（脚本即可，不进 git）；份量/热量估算达不到"量级感知"底线 → STOP 回 D1 改判，不提交端口扩展
### Phase 1: 公共端口扩展（先稳，带既有回归）
- [ ] `ImageBlock(media_type, data_base64)` 进 content 模型；两 provider 序列化 + 单测；**对未知/不可序列化 block 显式 raise（openai provider 现有 if/elif 链会静默丢弃未知 block——必须修）**；既有 chat 测试全量回归<!-- vj-plan-review: applied [adversarial/1] -->
### Phase 2: 识别 capability（test-first）
- [ ] `tests/test_meal_recognition.py`：结构化明细 / 10s 超时 / multi-dish / unrecognized / 5xx 降级保留照片 / 零副作用 / text 路径（≤200 字、AI 失败）
- [ ] service：photo_id → StoragePort 取图 → ImageBlock + json_schema prompt；text → TextBlock 同 prompt；错误翻译按 design.md API Delta 识别行为决策表

## 3. Technical Approach
### 方案
- 复用既有 LLM provider 栈（D1）；json_schema 输出 items[{name,portion,calories,protein,fat,carbs}] + status/reason
### 关键 API / 集成点
- `LLMPort.generate(..., json_schema=...)`（`application/ports/llm.py:149`；anthropic 走强制 tool call、openai 走 response_format）<!-- vj-plan-review: applied [feasibility/3] -->
- 503 映射复用 `core/exceptions.py` 的 `_business_code_to_http_status` 机制（既有 `SERVICE_UNAVAILABLE=40003` 为先例）
- `StoragePort` 签名 URL / 字节读取 - 仅取图，不管理文件生命周期（design.md §3c 边界）
### 集成模式（伪代码，5-10 行）
```pseudocode
input = ImageBlock(photo_bytes) if photo_id else TextBlock(text)
result = llm.generate([system_prompt, input], schema=MEAL_SCHEMA, timeout=10s)
if timeout/5xx -> raise BusinessException(AI_UNAVAILABLE)   # 照片不动，零写入
if result.items empty/low_conf -> return {status: unrecognized, reason}
return {status: ready, items}
```
### 错误处理
| Error | HTTP | When | message_key |
|------|------|------|------|
| AI_UNAVAILABLE（新增） | 503 | 超时/5xx/网络 | 新增 i18n key |
| NOT_FOUND | 404 | photo_id 非本人/不存在 | 复用既有 |
| PARAM_VALIDATION_ERROR | 422 | photo_id 与 text 都缺/都给/text>200 字 | 复用既有 |
### 日志
| Event | Level | Fields |
|------|------|------|
| meal_recognition.completed | info | source(photo/text), latency_ms, item_count, status |
| meal_recognition.failed | warning | source, reason(timeout/5xx), latency_ms |
### 备选（Rejected，引自 `decisions.md`）
- 专用食物识别 SaaS — D1；documents 式异步轮询 — D3；独立识别端口 — D7
### Execution note
- Test policy: test-first（外部调用降级 + 公共端口面）
- 复用声明: 必须扩展既有 LLMPort/providers，禁止另建 LLM 调用通道（D7）
- Fallback 约束: **禁止 fallback/mock/简化实现伪装识别成功**——AI 不可用时必须 fail closed（AI_UNAVAILABLE），不得返回默认/缓存明细；**图像必须真正传出**，provider 静默丢 block = 伪造明细，同属违禁（design.md 合同区 Must Hold）<!-- vj-plan-review: applied [adversarial/1] -->
### Stop conditions
- ImageBlock 扩展导致既有 chat provider 测试回归且无法在 write scope 内修复
- 需要改 `meal_records` 相关文件（违反零副作用不变量）
- 发现与 Story AC / catalog / anchors 冲突

## 4. Acceptance Criteria
> 投影自 Story 1.2 行为 AC 全部 7 条 + Story 1.5 行为 AC 中的后端 3 条（text happy/超长 422/AI 失败）；Story 1.5 的"失败保留输入"是前端行为归 T005，"记录同构"归 T004
- [ ] Given photo_id When 识别 Then 200 + items 含六字段；≤10s
- [ ] Given 风景照 When 识别 Then 200 + status=unrecognized + reason
- [ ] Given AI 超时/5xx When 识别 Then 503 AI_UNAVAILABLE；照片保留；零 meal_records 写入
- [ ] Given text="牛肉面一碗" When 补录 Then 200 + items；text>200 字 Then 422

## 5. Affected Components
### 实现
- 见 Write scope；副作用：外部 AI 调用（无 DB 写）
### 文档（必更）
- `docs/project/api/conventions.md` 若 AI_UNAVAILABLE 属全局错误码语义 → 报告（plan 已在 meal-log.md 声明，全局化由 reviewer 定）

## 6. Existing Code Impact
### 需重构
- 无（ImageBlock 为增量）
### 现有测试受影响
- `backend/tests/test_llm_anthropic_provider_tools.py` / `test_llm_openai_provider_tools.py` - 需确认 content 模型变更零回归
### 测试新增（test-first）
- provider ImageBlock 序列化 ×2 + **负向用例**：image-only 消息断言 wire payload 真含图像数据；未知 block 类型断言显式抛错（防静默 drop → 伪造明细）<!-- vj-plan-review: applied [adversarial/1] -->
- 识别用例（测试名与 story AC / verify.sh `-k` 过滤锚定）：`test_recognition_completes_within_10s`、`test_recognition_multi_dish_returns_multiple_items`、`test_recognition_unrecognized_returns_reason`、`test_recognition_downstream_failure_keeps_photo`、`test_recognition_failure_no_side_effects`、`test_recognition_text_input_returns_items`、`test_recognition_text_too_long_422`<!-- vj-plan-review: applied [coherence/4] -->

## 7. Definition of Done
- [ ] `pytest tests/test_meal_recognition.py -q` + 既有 LLM 测试全量绿（= `verify.sh U2` 可执行部分 + U5 的 `-k text`）
- [ ] 识别零副作用不变量有测试覆盖且绿
- [ ] test-first 执行；strict 逐 task 记录入 `_ledger.md`
- [ ] task done != U2/U5 done：ledger 标注 FE 归 T005、同构测试归 T004
- [ ] 未引入新决策；未修改 write scope 之外文件
