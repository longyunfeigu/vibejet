<!-- 重型 task 文档模板（A 方案：人话书挡 + 执行规格）。
     内容投影自 epic-plan 的 Appendix C，不重新发明 HOW；保留 test-first。
     读者导航：执行前看「摘要」，执行后看「变更叙事」，中间 1-7 段给 AI 执行/深度纠错。
     主生成方：vj-epic-plan Phase 5（写 plan 时一并生成）。vj-work 仅在 task 文档缺失时回退生成。
     ⚠️ 本文件与另一份 task-doc.template.md 是同步副本，改一处须改两处。 -->

# T{NNN} {Task 标题}

**Epic:** [Epic {N} {名称}](../../epics/{epic-file}) · **Unit:** {U-ID} {Story 名} · **Depends:** {前置 T-ID 或 无} · **Wave:** {波次} · **Status:** ☐ pending | ◐ in-progress | ☑ done | ⊘ skipped

## 摘要（人话 · 执行前看，30 秒懂意图）
- **为什么做**：{动机，1 句}
- **做什么**：{核心动作，2-3 句人话，不写库名/伪代码}
- **完成的标志**：{做完后可观察的状态}
- **一句话**：{一句话概括，便于转述}

---
〔以下 1-7 段为执行规格 —— 给 AI 执行 + 深度纠错用，平时可折叠忽略〕

## 1. Context
### 现状
- 当前存在什么 / 限制是什么（投影自 plan Appendix B + 前置 task 已交付物）
### 目标态
- 本 task 完成后应存在什么
### 继承假设
- A1 (FEASIBILITY): {引自 plan §2 决策，如 D1 服务端会话+HttpOnly Cookie}

## 2. Implementation Plan
### Phase 1: {描述}
- [ ] 步骤
### Phase 2: {描述}
- [ ] 步骤

## 3. Technical Approach
> 投影自 plan Appendix C 的 Approach / Patterns；约 200-300 字，给方向不写全量实现。
### 方案
- 框架/库 + 版本 + 标准（RFC/OWASP，若适用）
### 关键 API / 集成点
- `签名` - 用途；Where / How / When 集成
### 集成模式（伪代码，5-10 行）
```pseudocode
{方向性伪代码}
```
### 错误处理
| Error | HTTP | When | message_key |
### 日志
| Event | Level | Fields |
### 备选（Rejected，引自 plan §2）
- {方案} — 拒因

## 4. Acceptance Criteria
> 投影自 Story AC（信封 rewrite 后）。
- [ ] Given … When … Then …

## 5. Affected Components
### 实现（投影自 plan Appendix C Files: Create/Modify）
- `path` - 改动 + 副作用（DB写/事件/HTTP）+ 深度
### 文档（必更）
- `docs/project/...` - 契约同步

## 6. Existing Code Impact
### 需重构
- `path` - 为什么
### 现有测试受影响
- `path` - 为什么（仅列受影响的现有测试）
### 测试新增（test-first，本 task 要写）
> 标了 test-first 的 Unit，先写失败测试再实现。投影自 plan 的 Test scenarios。
- {happy / edge / error / integration 场景}

## 7. Definition of Done
- [ ] 所有 AC 满足
- [ ] test-first 测试先红后绿（Verification 命令全绿）
- [ ] 无遗留兼容垫片
- [ ] 文档已更新
- [ ] 代码已评审（vj-work Phase 4 review）

---

## 变更叙事（执行后回写 —— 你不用读代码就能转述 AI 做了啥）
- **实际做了什么**：{人话 3-5 句：实际建/改了什么、怎么工作的} _(待执行)_
- **怎么满足验收（对应 AC）**：{逐条对应 AC} _(待执行)_
- **关键权衡 / 偏离规格**：{为什么这么选；实现若偏离上面规格，写明原因} _(待执行)_
- **想深入看代码**：{commit SHA + 关键文件} _(待执行)_

<!-- ========================================================================
附：UI Unit Design context 注入块
生成 task 文档时，若该 Unit 的 Files: 含 .tsx，或路径含 routes/ features/ components/
→ 判定为 UI Unit，把下面整块原样复制到「## 3. Technical Approach」段末尾。
非 UI Unit（纯后端 / 纯配置 / 纯测试）不注入。
======================================================================== -->
<!--
Design context（UI Unit 必读）:
- 开工前先读现有前端 theme / layout / component patterns，再读设计合同；不要另起一套风格。
- 设计合同读取顺序：优先 `docs/project/DESIGN.md`；缺失时 fallback `docs/project/design_guidelines.md` 并在变更叙事标注；两者都缺失时暂停 UI 实现，先给出轻量 Design Read 或补 `DESIGN.md` 草案。
- 读取并遵循 epic.md `## 页面体验地图` 中本 Unit 对应的页面/区域：页面职责、主操作、次操作、关键状态、信息优先级、体验护栏。
- 如有 `docs/reference/research/designs/{epic-id}/` 设计稿或提示词，作为页面结构和状态参考；不得在 vj-work 执行期临时从 vibeui/awesome-design-md 自动挑新风格。
- 加载并遵循 design-taste-frontend skill 的防默认风格规范，但项目 `DESIGN.md` 优先级更高。
- 禁止 AI 默认风格：紫色/蓝色渐变背景、三等份 feature 卡片、Inter 字体、通用 glassmorphism。
- 若项目使用 MUI：TextField 优先 outlined + 左侧 InputAdornment 图标；主操作 Button 视觉权重最高；Paper/Card 半径和阴影遵循 `DESIGN.md` 或现有 theme。
- 页面级布局：列表/仪表盘优先信息密度和扫描效率；主操作清晰，次操作降噪；背景用浅色或白色，不用深色渐变。
- 前端完成前必须做视觉验收：桌面 + 移动截图；无文字溢出、无元素重叠；空态/加载/错误/成功/无权限状态完整；主操作首屏可见；截图与 `DESIGN.md` 和页面体验地图一致。
-->
