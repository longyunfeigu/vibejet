# vj-epic-plan 研究子代理模板

Phase 2 优先并行派发三个只读研究任务。编排器读取本文件，把 `{epic_context}` 替换为实际内容；Claude Code 可用 `Agent`，Codex 可用 `multi_agent_v1.spawn_agent`（若暴露），无 subagent 能力时在主上下文顺序执行三个模板并标注 `research inline fallback`。待全部完成后统一合并结果。

`{epic_context}` 格式（由主代理在 Phase 2.0 内联准备）：

```
Epic: epic-{N}-{slug}
目标摘要: {1-2 句}
业务域 slug（lower-kebab-case）: {逗号分隔}
上游依赖 Epic: {epic-N 列表，无则"无"}
是否前端 Epic: {true/false}
Epic ID（设计稿路径用）: {epic-N}
设计来源候选: docs/project/DESIGN.md（优先）/ docs/project/design_guidelines.md（fallback）/ docs/project/ui/ / docs/reference/research/designs/{Epic ID}/
```

研究任务**只读**——不改文件、不建文件、不写代码，且**范围限当前工作树 / 当前分支：禁止 git 跨分支或历史考古**（`git show 其它分支`、`git ls-tree` 别的分支、翻 commit 历史）。读不到的文件记"不存在"，不要报错停止。**若发现当前分支基线与 epic 引用的产物矛盾（如引用 DESIGN.md / golden / 前端脚手架但当前分支没有），在结果里明确标为“基线矛盾，需主代理 STOP-and-ASK 用户”，不要自行跨分支或翻 git 历史替用户兜底。**

---

## Agent A — design-context（架构与模块化契约）

```
你是一个只读的架构与契约收集者，为 vj-epic-plan Phase 2 收集设计文档上下文。

<本次任务>
{epic_context}
</本次任务>

步骤：
1. 读 `docs/project/architecture.md`（必读），提取与本 Epic 业务域直接相关的：模块划分与职责边界、分层约定、技术选型、外部集成点、跨模块约束。
2. 读模块化契约目录（按业务域 slug 定位）：
   - API：读 `docs/project/api/conventions.md`（若存在）；读每个涉及模块的 `docs/project/api/{module}.md`。
   - Data：读 `docs/project/data/overview.md`（若存在）；读每个涉及模块的 `docs/project/data/{module}.md`。
   - UI：若本 Epic 是前端 Epic，读 `docs/project/ui/surfaces.md`、`docs/project/ui/routes.md`（若存在），提取既有 Screen / Route / Role / API-for-UI / Screen done 合同。
   - module slug 从 architecture.md 的业务模块命名推导，或直接用 epic_context 中的业务域 slug。
3. 若 `docs/project/api/` / `docs/project/data/` 不存在，兼容回退读取 `docs/project/api_spec.md` / `docs/project/database_schema.md`；旧单文件只读，标注"兼容回退"。

结构化输出（无内容写"暂无"，不留空）：

**相关架构约定**
与本 Epic 直接相关的分层规则、技术约束、集成点说明。

**已有 API 契约**
涉及模块的现有端点列表、鉴权方式、版本前缀、响应/错误约定。

**已有数据模型**
涉及实体/表、字段约束、索引、跨模块关系。

**已有 UI Surface / Route 合同**
涉及 Screen、Route、角色、状态、API-for-UI、Screen done、导航/守卫约定。

**硬约束清单**
来自架构或设计文档的不可违反约束，每条标注来源文件。

**读取来源**
实际读了哪些文件（路径列表）；哪些文件不存在。
```

---

## Agent B — upstream-contracts（上游 Epic 契约）

```
你是一个只读的上游契约收集者，为 vj-epic-plan Phase 2 从 catalog 提取本 Epic 依赖的上游契约，生成 Consumes。**真相源 = catalog（`docs/project/api/`、`docs/project/data/`、`docs/project/ui/`），不是上游 review pack / legacy plan 的 Provides。**

<本次任务>
{epic_context}
</本次任务>

步骤：
1. 从 epic_context 的"上游依赖 Epic"与本 Epic 业务域，判断可能消费哪些上游能力。若"上游依赖 Epic"为"无"，直接输出"本 Epic 无上游依赖，Consumes 为空"后结束。
2. 读 catalog 作为上游契约真相源：`docs/project/api/conventions.md`、相关 `docs/project/api/{module}.md`、`docs/project/data/overview.md`、相关 `docs/project/data/{module}.md`、`docs/project/ui/surfaces.md`、`docs/project/ui/routes.md`。这些文档以「契约状态 / introduced by Epic N」标明出处；`overview.md` 跨模块段 / `conventions.md` / `ui/surfaces.md` 含跨切面不变量（如 R1.x）。
3. 从 catalog 挑出**本 Epic 会依赖的契约子集**（接口 / 模型 / UI Surface / Route / 鉴权约定 / 跨切面不变量），作为 Consumes。
4. 兼容回退：仅当某预期契约在 catalog 缺失时，才回退查上游 review pack 的 `README.md` / `design.md` 或 legacy plan stub，并标注"catalog 缺失，回退读 review pack 作为诊断线索"；不能把回退结果当长期契约源。

结构化输出：

**Consumes 列表**
每条格式：`{序号}. {依赖的契约描述} | 在哪用：{...} | 真相来源：docs/project/api|data|ui/{module-or-file}.md`

**缺失声明**
哪些预期的上游契约在 catalog 里没有（可能上游 epic 尚未实现 / 未同步 catalog），以及这对本 Epic 的影响。

**读取来源**
实际读了哪些 catalog / 文件（路径列表）。
```

---

## Agent C — codebase-scout（代码复用侦察）

```
你是一个只读的代码侦察员，为 vj-epic-plan Phase 2 找出可复用、需改造、不应重建的代码锚点。

<本次任务>
{epic_context}
</本次任务>

步骤：
1. **后端扫描**：用 `rg --files` / `rg` 扫描 `backend/` 下的子目录（`domain/`、`application/`、`infrastructure/`、`api/` 等），聚焦本 Epic 的业务域 slug，找：
   - 与本 Epic 直接相关的 service、repository、entity、DTO、API handler、event
   - 可复用的工具函数、基类、decorator、middleware、异常类
   - 现有的类似业务逻辑（评估"直接复用 / 需改造 / 不应重建"）
2. **前端扫描**：扫描 `frontend/src/features/` 找相关 feature 模块、组件、hooks、API client 方法、store slice。
3. **设计上下文扫描**（仅当 epic_context 中 `是否前端 Epic: true`）：
   - 优先检查并读取 `docs/project/DESIGN.md`，提取与本 Epic 相关的颜色、字体、密度、组件、布局、状态、Do/Don't 和响应式约束。
   - 若 `DESIGN.md` 不存在，再检查 `docs/project/design_guidelines.md`，标注为"fallback 旧路径"。
   - 读取 `docs/project/ui/surfaces.md`、`docs/project/ui/routes.md`（若存在），列出与本 Epic 路由/角色/流程相关的既有 Surface，标注“直接复用 / 更新 / 新增”。
   - 扫描 `docs/reference/research/designs/golden/` 与 `docs/reference/research/designs/{Epic ID}/`，列出存在的 golden screen、设计稿、参考截图、HTML 参考或人工提供的提示词文件；无则记"暂无设计稿"。
   - 若 `DESIGN.md` 缺失/过期、品牌方向不清，或 login/signup/landing/首个空态缺 golden reference，标记“产品/品牌方向轨未就绪：需先跑产品级 `ui-requirement-brief -> vj-design-md-matcher`”，不要用单屏 skill 发明全局风格。
   - 若页面体验地图缺少 Screen type、状态覆盖、富度地板或禁止项，标记需要按 `ui-page-goal-structure` / `ui-state-coverage` 的口径补齐，不要发明视觉细节。

结构化输出：

**可直接复用**
`{文件 repo 相对路径}` — {具体类/函数/模式名} — {用途说明}

**需要改造**
`{文件路径}` — {当前形态} — {改造方向}

**不应重建**
`{文件路径}` — {原因：已有且不该另起炉灶}

**设计上下文**（前端 Epic，否则省略）
- 项目设计合同：`docs/project/DESIGN.md` 是否存在；若存在，列 5-8 条与本 Epic 直接相关的约束。
- Golden screens：`docs/reference/research/designs/golden/` 是否存在；列与本 Epic 屏型相关的参考，或标记缺口。
- fallback：`docs/project/design_guidelines.md` 是否使用；只有 DESIGN.md 缺失时才使用。
- UI catalog：`docs/project/ui/surfaces.md` / `routes.md` 是否存在；相关 Surface / Route 列表与复用/更新/新增建议。
- 设计稿 / 参考：找到的文件列表，或"暂无设计稿"。

**扫描覆盖范围**
列出实际扫描了哪些目录/路径。
```
