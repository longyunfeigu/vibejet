# vj skill 家族约定（编写 / 修订 checklist）

新建或大改 `.agents/skills/` 下的 vj 系 skill 时逐条对照。目的：让所有 skill 在
无人值守行为、失败兜底、真相源指向和验证方式上保持同一代水平，避免再出现
"某个 skill 落后一代"的漂移。

## 结构

- [ ] SKILL.md 只留：适用/不适用场景、铁律、Phase 骨架、触发示例；长模板、展示格式示例、
      派生技术表下沉 `references/` 按需读（参照 `vj-epic-plan` 的结构）
- [ ] frontmatter `description` 包含用户会说的触发短语（中文口语 + 英文关键词）
- [ ] 与上下游 skill 的协作链显式声明，且**引用的 skill 必须真实存在**
      （交付前 `rg` 验证，杜绝 run-story 式断链）

## 行为

- [ ] **无人值守 fallback**：每个 user gate（确认/审批/提问）都定义无法提问时的行为——
      写最合理假设 + `Confidence: H/M/L`，标"假设待审批"，不阻塞、不静默拍板、不静默跳过
      （口径源：`vj-epic-plan` Phase 3）
- [ ] **失败模式与兜底表**：列出真实会卡住的场景（触发条件 / 一线修复 / 仍失败兜底），
      不假设用户配合、网络可用、路径可写（格式参照 `vj-product-requirements`）
- [ ] **Stop conditions**：同一确认 gate 反馈 ≥3 次不收敛 → 弹"继续 / 重审上游 / 放弃"，
      防死循环
- [ ] **后置审查钩子**：文档产出类 skill 收尾自动触发独立审查（PRD/架构 → `codex-review`；
      epic plan → `vj-plan-review`），用户可说"跳过审查"

## 真相源（只写一处，其余指针）

- [ ] 规划期 UI 合同规则 → `.agents/skills/_shared/ui-planning-contract.md`
- [ ] 实现期前端出口闸（富度 R / 工艺 C / A/B 轨）→ `.claude/rules/frontend.md`
- [ ] 设计 token 数值 → `docs/project/DESIGN.md`
- [ ] 跨 Epic 稳定契约 → `docs/project/api|data|ui/` catalog（architecture.md 不重复维护
      端点/表级细节）
- [ ] Epic/Story 编号与状态 → `docs/tasks/kanban_board.md`
- [ ] 学习飞轮：写端 `vj-compound`（`docs/solutions/`），读端 Agent D 模板
      （`vj-epic-plan/references/research-agents.md`）
- [ ] 文档 HTML 视图（`.md`=唯一事实源，`.html`=派生、不进 git、永不手编）→
      `.agents/skills/_shared/scripts/render_doc_html.py` 头注释；文档产出类 skill
      收尾跑它生成人读视图（PRD / epic / review pack 已接入，新的人读文档产出照此办理）
- [ ] 新 skill 不复述以上任何一处的规则条目；引用格式："按 {路径} §N 执行，本 skill 不复述"

## 验证

- [ ] 可确定性判定的约束写成 `scripts/` 机检脚本（exit code 拦截），不靠模型自查清单
      （参照 `vj-epic-story/scripts/validate_story.py`、`vj-compound/scripts/validate-frontmatter.py`）
- [ ] 判定权独立：质量闸的 pass/fail 不得由产出方自评（参照 frontend.md A5/B5）
- [ ] 图形默认 Mermaid；仅纯文本终端环境降级 ASCII

## 红线

- [ ] 敏感数据：不写真实 secrets、客户数据、业务原文进任何产物
- [ ] 不做投机抽象：skill 只解决当前工作流的真实卡点，不为"以后可能"加配置项
