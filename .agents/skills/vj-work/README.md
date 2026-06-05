# vj-work

消费 `vj-epic-plan` 产出的 **epic 实现计划**，把它系统化落地成已实现、已验证、已提交的代码。

## 在工作流中的位置

```
vj-epic-story (WHAT)
      ↓
vj-epic-plan  (HOW: 实现计划 + task 文档 + Unit 波次)
      ↓
vj-work       (执行: 本 skill —— 装载 task → 消费 plan 波次 → 隔离执行 → 验证 → 提交)
      ↓
vj-compound   (沉淀: 把踩的坑/取舍写回 docs/solutions/)
```

## 三大核心能力

1. **装载 task**：默认一个 Implementation Unit（Appendix C）对应一个 task，携带 Depends / Execution note / Verification。
2. **消费 plan 波次**：以 `vj-epic-plan` 写入 `_ledger.md` / Appendix D 的波次为真相源；执行期只做当前波次的廉价文件交集护栏，不重算全局依赖。
3. **subagent 并行执行**：一波内多个 Unit 只有在运行时具备 subagent + 独立写入隔离能力时并行落地；否则显式记录 runtime fallback 后串行执行。长依赖链（无并行机会）用 serial subagents 或内联执行给每个 Unit 隔离上下文。

## 可 Review 性与收尾

- **重型 per-task 文档 + 总账**（`work_dir`）：与 ce-work（只靠易失 harness 任务列表 + commit/PR）不同，vj-work 在 `docs/tasks/work/epic-{N}-{slug}/` 落一套可 Review 产物——`_ledger.md`（总账/索引）+ 每个 task 一份 7 段文档（`references/task-doc.template.md`）。每份 task 文档含**规格（执行前）+ 执行结果（执行后回写实改文件/验证/commit）**：规格让你在 AI 动代码前 Review 意图，执行结果让你知道它实际改了什么。
- **审批门**（`approval_gate`）：全部 task 文档生成后停下待用户批准，再动代码——"心理有底"的最强保障。
- **发布前 code review（必做）**：收尾对整个 diff 跑一次 review，敏感面/大改时升级。注意这是**执行后审 diff**，与 `vj-plan-review` 审计划是两回事。
- **Final Validation**：逐条核对 plan 的 `Requirements`(R-ID) 与 `Deferred to Implementation` 已解决，再翻转 plan `status: active → completed`。

## 关键设计取舍

- **站 `ce-work` 肩膀，但自包含**：只借 compound `ce-work` 的执行机制（Unit 驱动循环、文件交集并行安全检查、写入隔离、增量提交、System-Wide 测试检查、边做边简化），按 vj 轻量风格自实现，**零插件耦合**——不依赖 compound 插件、不调 ce-* agent。
- **不选 `ln-1000` 当肩膀**：它是看板/Linear 驱动的重型状态机，并行靠预先标 `Parallel Group`，而非自动文件依赖分析；且绑外部 runtime。形状不符。
- **校验与执行分离**：计划级语义校验由独立 skill `vj-plan-review` 在 vj-epic-plan 定稿前处理；vj-work 只保留执行期薄护栏（当前波次文件交集、文件/模块存在性、已完成检测）。
- **plan 是决策依据不是脚本**：不改 plan 正文，进度由 git commit 承载；唯一允许的改动是收尾翻转 `status: active → completed`。

## 输入

```
vj-work docs/tasks/plans/<...>-plan.md   # 指定 plan
vj-work epic-1                           # 按编号定位
vj-work                                  # 取最新 plan
```

## 文件

- `SKILL.md` — 5 Phase 工作流（定位 → 装载 task → 审批波次 → 执行 → 收尾）
- `README.md` — 本文件

## 运行时适配

- Claude Code：优先用 `Agent` + worktree isolation 并行。
- Codex：仅在 `multi_agent_v1.spawn_agent` 具备 forked workspace / disjoint write set 集成能力时并行；否则串行并在 `_ledger.md` 记录 runtime fallback。
- 无 subagent 能力：串行执行，不视为计划错误。
