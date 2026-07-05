---
title: "Epic 1 拍照记录一餐 Decisions"
type: epic-decisions
status: active
date: 2026-07-05
epic_id: "1"
---

# Epic 1 拍照记录一餐 Decisions

本文件是 D-ID / ACD-ID 的唯一真相源。其他 human docs 和 task docs 只引用 ID，不复制完整论证。

> 本 plan 无人值守生成：以下 assumed 状态的决策均为"假设待审批"，等 reviewer 批准或改判。
> **catalog 已按当前假设同步（synced, pending review）**：任一 D 改判（尤其 D2/D5/D6/D7 涉及端点/枚举/schema）时，须随终稿重生对应 catalog 文件与受影响 task docs，不允许只改 decisions。<!-- vj-plan-review: applied [coherence/2] -->

## 1. Pending Decisions

| ID | Status | Question | Recommended stance / assumption | Impact | Alternatives / Rejected |
|----|--------|----------|---------------------------------|--------|--------------------------|
| D1 | assumed (Confidence: M) | AI 识别服务选型（PRD §10.3 开放问题） | 复用仓库既有 LLM provider 脚手架（`backend/infrastructure/external/llm/`），用多模态 chat + 结构化输出 prompt 做菜品识别与营养估算；不引入专用食物识别 SaaS | 决定成本/延迟/识别质量上限；影响 U2/U5 全部 | 专用食物识别 API（新外部依赖 + 独立计费 + 集成面翻倍；估算质量未必更好，V1 先验证产品假设） |
| D2 | assumed (Confidence: H) | 餐食照片存储走哪条链路 | `POST /api/v1/meal-photos` 为**薄端点**：叠加 meal 特定校验（仅 image/*、≤10MB、非空），内部委托既有 file_asset 上传服务（`/api/v1/storage/upload` 同一条链路，owner-scoped 继承），`photo_id` 即 file asset id；不自建存储表 | U1 实现方式；照片保留策略（PRD §10.3）随 file_asset 现状，V1 不做清理策略 | ①前端直用 `/api/v1/storage/upload`（meal 校验规则无处安放，且 Story 1.1 AC 端点需回改）；②自建 meal 专用存储表（重复造已有权威实现，违反复用红线） |
| D3 | assumed (Confidence: M) | 识别调用同步还是异步任务 | 同步请求 + 10 秒超时（PRD §5.1），超时即走降级路径；不引入队列 | U2 的实现形态与前端交互（识别中态是一次请求的等待，不是轮询）。已知取舍：同步方案把已付费的 AI 结果绑在客户端连接上，识别路径无幂等，弱网断连重试=重复计费（Risks 观察项） | **仓库真实异步先例是 documents 的 FastAPI BackgroundTasks + 轮询**（零队列基础设施，pending→ready/failed 落盘）：被拒理由是 V1 单用户下轮询引入状态存储+前端轮询双重复杂度，而 10s 单次等待 + 文本补录兜底已满足 PRD 降级要求；若 Q2 实测超时率高则改判走 documents 模式（非 Celery——Celery 是稻草人已修正）<!-- vj-plan-review: applied [adversarial/2] --> |
| D4 | assumed (Confidence: M) | 修正后的营养数值以谁为准 | 前端按比例即时重算（Story 1.3）负责**展示**；保存时后端校验结构与取值合法，**记录 totals 由服务端从 items 求和**（API 不收 total 字段）。"伪造"对单用户是伪命题——真实风险是前端重算 bug，服务端求和即交叉校验<!-- vj-plan-review: applied [adversarial/5] --> | U3/U4 边界 | 后端权威重算/重估接口（多一次往返，修正交互出现可感知延迟，收益为零；求和≠重估） |
| D5 | assumed (Confidence: H) | 餐次枚举与默认值 | `breakfast/lunch/dinner/snack`；按本地时间段给默认值（05-10 早/10-15 午/15-21 晚/其余加餐），用户可改 | U4 数据模型与前端默认值逻辑 | 自动推断算法（PRD §11.2 明确可延后） |
| D6 | assumed (Confidence: M) | 文本补录与拍照识别的端点关系 | 共用 `POST /api/v1/meal-recognitions`，请求体 `photo_id` 与 `text` 二选一，返回同构明细 | U5 与 U2 共享识别通道与错误语义；前端确认流程完全复用 | 独立 text-entries 端点（两套错误语义与明细 schema，确认流程要写两份） |
| D7 | assumed (Confidence: M) | 既有 `LLMPort` 无图像 block，照片喂不进模型（研究实锤：`ContentBlock` 只有 Text/ToolUse/ToolResult） | **扩展 `LLMPort` 的 content 模型新增 `ImageBlock`**（base64 source），anthropic/openai 两个 provider 同步实现；meal 识别用既有 `json_schema` 结构化输出返回菜品明细。这是公共端口契约变更（strict trigger，已计入 policy） | U2/U5 的实现根基；同时给基础库沉淀通用多模态能力 | 另立 meal 专用识别端口 + 独立适配器（造第二条 LLM 通道，违反基础库"每种能力只保留一个 canonical 参考"的家规） |
| D8 | assumed (Confidence: H) | 设计稿路径不符约定（实际在 `designs/prd-suishou-shiji/`，约定为 `designs/{epic-id}/`） | plan 与 task 引用现路径 `prd-suishou-shiji/ui-mock-board.html`；执行期参考图前置闸产出的截图落 `designs/epic-1/`，不搬移原稿 | task 文档的设计稿指针口径 | 现在搬移/复制原稿到 epic-1/（对一个 HTML mock 做文件搬运没有收益，链接即可） |
| D9 | assumed (Confidence: M) | 保存防重复提交的幂等机制 | 复用基座 `IdempotencyService`（Redis/Noop），照抄 `presign-upload` 模式：前端每次进入确认区生成 `Idempotency-Key` 并**存 sessionStorage**（收窄刷新窗口），重试沿用。已知残余窗口：杀进程/清会话 mid-flight 不去重，且本 Epic 无删除入口无法补救（编辑/删除归 Epic 4）——显式接受<!-- vj-plan-review: applied [adversarial/4] --> | U4 Edge AC（双击/网络重试只产生一条记录）的实现口径 | 仅前端禁用按钮（网络层重试仍会重复创建）；DB 唯一约束去重（缺乏自然唯一键，需引入人造列） |

## 2. AC Deviations

> 以下为 vj-plan-review 发现、需回改 WHAT 层（story/epic.md）的事项。按闸规则不静默改，待 reviewer 批准后回改。<!-- vj-plan-review: applied [scope/2][ui-surface/1-2][scope/3] -->

| ID | Source AC | Original acceptance | Planned stance | Equivalent? | Handling |
|----|-----------|---------------------|----------------|-------------|----------|
| ACD1 | Story 1.2 FE AC | 无"AI 首次使用确认"相关 AC | PRD §5.3 是 Must Hold：plan 侧已在 Screen Contract 增"首次发送授权确认"一等态（T005 Screen done 覆盖）；建议回改 story 1.2 增补 1 条 FE AC（`Browser 首次发起识别 → [data-testid=ai-consent] 可见且确认后不再出现`） | partial（合同已可执行，AC 追溯缺口） | pending approval |
| ACD2 | Story 1.1 FE AC | 后端 422 有 AC，前端"上传失败态"呈现无 AC | Screen Contract 已增"上传失败"态；建议回改 story 1.1 增补 1 条 FE AC（`Browser 上传超限/非图片 → [data-testid=upload-error] 可见且保留重选入口`） | partial | pending approval |
| ACD3 | epic.md System-Wide「已下放 Story 1.4 Integration AC」 | epic 声称"记录含可聚合营养字段"已下放 1.4，实际 1.4 Integration AC 只有 ownership | 数据模型已含快照列（design §6）；建议回改：epic 措辞修正，或 story 1.4 补 1 条快照字段 AC 使追溯闭合 | yes（实现无差） | pending approval |

## 3. Approved Decisions

暂无（无人值守运行，全部决策处于 assumed 状态待审批）。

## 4. Scope Boundaries

### In Scope

- Epic 1 全部 5 个 Story：照片上传、AI 识别、明细修正、确认保存、文本补录
- meal 模块的 domain/application/infrastructure/api 四层 + Alembic migration
- `/record` 单屏前端（含全部状态）与登录守卫
- catalog 同步：`docs/project/api/meal-log.md`、`docs/project/data/meal-log.md`、`docs/project/ui/surfaces.md` + `routes.md`

### Out of Scope / Deferred

- 今日聚合与首页总览（Epic 2）、目标设置（Epic 3）、历史趋势（Epic 4）
- 餐次自动推断、多张照片、补记历史时间（记入 Story Assumptions）
- 照片清理/保留策略（PRD §10.3 开放问题，V1 不做）
- AI 调用成本护栏（PRD §10.3，V1 单用户暂不做，记入 Invariants/Risks 观察项）
