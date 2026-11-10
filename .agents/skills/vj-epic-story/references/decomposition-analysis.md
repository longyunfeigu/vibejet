# Epic 信息抽取与隐藏影响扫描

`vj-epic-story` Phase 2.6 使用本参考。每个 Epic 只跑一次，输出统一进入 Phase 5 的单一
Intent Gate，不在中途反复提问。

## 1. Auto-Extract

| 字段 | 主源 | 备源 | 缺失标记 |
|------|------|------|----------|
| 业务目标 | PRD Epic 理由 | PRD 核心价值（⚠️ 推断） | ❓ |
| In Scope | PRD 该 Epic 需求 | Architecture 模块职责 | ❓ |
| Out of Scope | PRD 可延后能力 | PRD 非目标（⚠️ 全局） | ❓ |
| 用户旅程 | PRD 显式旅程/关键步骤 | 功能需求 + UI 设计稿（⚠️ 推断） | ❓ 必问 |
| 页面体验地图 | PRD/UI 设计稿/DESIGN.md | 旅程 + PRD 推断（⚠️） | 前端 Epic ❓ 必问 |

前端 Epic 额外抽取屏型、首屏品牌/任务要求、状态覆盖和参考来源。双轨与复杂流程判定按
`.agents/skills/_shared/ui-planning-contract.md` §2/§3。产品/品牌方向缺失时，把
`ui-requirement-brief -> vj-design-md-matcher` 列入 Intent Gate，不直接推进 UI Story。

标记规则：精确来源为 ✓；合理推断为 ⚠️；完全找不到为 ❓。所有 ⚠️/❓ 合并展示。

## 2. 用户旅程与页面地图

抽取优先级：PRD 显式旅程 → PRD 关键步骤 → EARS 条件与依赖 → UI 设计稿 → DESIGN.md。
Architecture/API/Data 只校验可落地性，不作为用户旅程主来源。

输出：

- Mermaid 主路径，使用业务语言，不画内部 API/表/服务。
- 主旅程：步骤、入口、用户行为、系统响应、覆盖 Story/AC。
- 分支/异常：未登录、无权限、空态、重复操作、下游失败、非法输入及覆盖 Story/AC。
- 前端 Epic 页面体验地图：职责、屏型、主/次操作、状态、信息优先级、品牌/富度、禁止项。

每个主步骤必须映射 Story；每个异常必须映射 Edge/Error AC 或独立 Story。跨 Story 路径落
Epic 旅程，单 Story 内流程落 Story AC。页面体验地图完整度按 UI planning contract §1/§4/§5，
缺字段回对应 `ui-*` skill。

## 3. System-Wide 六维扫描

从 Architecture、API catalog、Data catalog 和现有 Epic 扫描：

1. 跨模块影响
2. 不变量保护
3. 状态生命周期、并发、缓存、重试、清理与长事务
4. API 表面与其他消费者一致性
5. 错误跨层传播
6. 角色、资源所有权与越权边界

每项只能：拆新 Story，或进入现有 Story AC。落不进 AC 的决策进入 PRD open questions / plan
`decisions.md`；repo 级约束只引用 AGENTS/catalog，不重复落盘。Epic 不生成无消费者的
System-Wide section。

## 4. Batch Decisions

按 `references/display-formats.md` §C 展示 ✓/⚠️/❓、旅程、页面地图、六维扫描处置、Story
候选和 AC 增强。若同一 Intent Gate 三轮仍不收敛，回 Phase 2.1 重审 Epic 边界。
