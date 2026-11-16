---
name: vj
description: Route and execute Vibe Engineering work through the smallest reliable VJ delivery track. Use for “用 vj 做/处理/实现”, “走 vibe engineering workflow”, workflow selection, or when another vj skill needs to decide between a direct patch, a bounded Story, and a written plan (vj-plan → vj-work).
---

# VJ 交付路由

选能产出可观察证据的最轻交付轨。轨越重，文档和等待越多；只有出错代价高时才值得。

## 选轨

| 轨 | 什么时候用 | 产物 |
|----|-----------|------|
| **Patch** | 局部修复或调整，行为明确，没命中 strict 触发条件 | 改动 + 验证证据 |
| **Story** | 一个有边界的用户可见能力（通常 2-5 个文件，或一个前端/后端切片），没命中 strict 触发条件 | 简短意图 + 改动 + 验证证据 |
| **Plan** | 多个能力或跨 bounded context，或命中任一 strict 触发条件，或要做整份 PRD / 其中一个 Epic | 计划文档（`vj-plan`，整份 PRD 拆成每块一份）→ 执行（`vj-work`）→ 证据 |

strict 触发条件只在 `AGENTS.md`「Plan 规范」维护。会改变行为的歧义在澄清前按 strict 处理。

## 开工前

在回复里用几行说清：

- **意图**：要什么结果、不做什么、怎样算做完、还有哪些未决选择。
- **执行**：选哪条轨、会改哪些地方、用什么命令验证、是否 commit。

需求清楚、改动可逆时直接开工，不要确认。只在两种情况停一次：未决的产品选择会改变可观察行为；
或要执行破坏性、安全、迁移、外部副作用类动作而风险还没被用户认可。用户已明确授权的风险不再问。

用户说"不要 commit"时，所有工作流里的 commit 步骤都跳过；这不影响验证和 review。

## 各轨怎么做

**Patch**：读受影响代码和调用点 → 复现问题或写出会失败的断言 → 窄改动 → 定向验证 →
按 `AGENTS.md` 的 review 触发条件决定是否 review。不建 Story/Plan 文档。修 bug 时在回复里写一句根因
（为什么会错，不只是哪行错），并用 `rg` 搜一遍同样写法的其他位置，一起修或列出来。

**Story**：按会话里的简短计划直接实现，不建文档。跑定向测试和相邻影响检查，按 review 触发条件 review。
途中出现 strict 触发条件或跨上下文依赖时升级为 Plan。

**Plan**：`vj-plan` 出一份计划文档（整份给人审）→ `vj-work` 读代码、把验收变成测试、按执行顺序做完。
跨任务端到端风险值得时再跑 `vj-test`。进度和验收说明都写回那份计划文件。

## 收尾

报告改了哪些文件、跑了哪些验证（附真实输出）、还剩什么风险。必需的检查失败就如实报失败，
不要说成完成。
