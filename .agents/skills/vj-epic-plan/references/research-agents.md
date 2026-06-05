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
设计来源候选: docs/project/DESIGN.md（优先）/ docs/project/design_guidelines.md（fallback）/ docs/reference/research/designs/{Epic ID}/
```

研究任务**只读**——不改文件、不建文件、不写代码。读不到的文件记"不存在"，不要报错停止。

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
   - module slug 从 architecture.md 的业务模块命名推导，或直接用 epic_context 中的业务域 slug。
3. 若 `docs/project/api/` / `docs/project/data/` 不存在，兼容回退读取 `docs/project/api_spec.md` / `docs/project/database_schema.md`；旧单文件只读，标注"兼容回退"。

结构化输出（无内容写"暂无"，不留空）：

**相关架构约定**
与本 Epic 直接相关的分层规则、技术约束、集成点说明。

**已有 API 契约**
涉及模块的现有端点列表、鉴权方式、版本前缀、响应/错误约定。

**已有数据模型**
涉及实体/表、字段约束、索引、跨模块关系。

**硬约束清单**
来自架构或设计文档的不可违反约束，每条标注来源文件。

**读取来源**
实际读了哪些文件（路径列表）；哪些文件不存在。
```

---

## Agent B — upstream-contracts（上游 Epic 契约）

```
你是一个只读的上游契约收集者，为 vj-epic-plan Phase 2 提取本 Epic 依赖的上游 Provides。

<本次任务>
{epic_context}
</本次任务>

步骤：
1. 从 epic_context 的"上游依赖 Epic"字段取出每个上游编号（如 epic-1、epic-3）。若字段为"无"，直接输出"本 Epic 无上游依赖，Consumes 为空"后结束。
2. 用 `rg --files docs/tasks/plans/ | rg "epic-{N}-.*-plan\\.md$"` 查找每个上游 Epic 对应的最新 plan 文件（有多个取日期最新的）。
3. 从每个上游 plan 中**只提取** `## 3. 跨 Epic 契约` → `### Provides` 段（兼容旧 plan 时回退找 `§0.5 Provides`）。不读整个 plan。
4. 若某上游 Epic 没有对应 plan，或 plan 没有 Provides 段，记"epic-{N}：暂无 plan / Provides 未声明"。

结构化输出：

**Consumes 列表**
每条格式：`{序号}. {能力/接口/模型描述} | 来源：{上游 plan 路径 § 章节 或 docs/project/api|data/{module}.md}`

**缺失声明**
哪些上游 Epic 无 plan 或无 Provides，以及这可能影响本 Epic 的哪方面。

**读取来源**
实际读了哪些文件（路径列表）。
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
   - 扫描 `docs/reference/research/designs/{Epic ID}/`，列出存在的设计稿与 vj-ui-mock 产出的提示词文件；无则记"暂无设计稿"。

结构化输出：

**可直接复用**
`{文件 repo 相对路径}` — {具体类/函数/模式名} — {用途说明}

**需要改造**
`{文件路径}` — {当前形态} — {改造方向}

**不应重建**
`{文件路径}` — {原因：已有且不该另起炉灶}

**设计上下文**（前端 Epic，否则省略）
- 项目设计合同：`docs/project/DESIGN.md` 是否存在；若存在，列 5-8 条与本 Epic 直接相关的约束。
- fallback：`docs/project/design_guidelines.md` 是否使用；只有 DESIGN.md 缺失时才使用。
- 设计稿 / 提示词：找到的文件列表，或"暂无设计稿"。

**扫描覆盖范围**
列出实际扫描了哪些目录/路径。
```
