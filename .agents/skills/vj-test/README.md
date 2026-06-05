# vj-test

在 `vj-work` 把一个 epic 实现完之后，为它做**全自动跨层 E2E 测试**。人只读报告，不做手工测试。

## 在工作流中的位置

```
vj-epic-plan (HOW)
      ↓
vj-work   (实现：per-task test-first 单元/集成测试)
      ↓
vj-test   (跨层 E2E：本 skill —— 单 task 写不出的端到端流程)
      ↓
vj-compound (沉淀)
```

## 解决什么问题

vj-work 的 per-task test-first 只能测单个 task 自身的逻辑；**跨 task 的端到端流程**（前端登录 → 会话落 DB → /me 返回用户）单 task 写不出来。vj-test 在实现完成后专门补这层，断言**真实状态**：DB 行、缓存条目、API 信封、前端渲染。

## 关键设计（一句话版，权威定义见 `SKILL.md` 铁律 / 安全边界）

- **全自动 + 无人工闸**：人只读 `_test-report.md`，不做手工测试。
- **绿 ≠ 有效（变异自检）**：代码级测试过"改坏→变红"才算可信，测不到的判无效——替代人工闸的自动信任机制。
- **前端走 `web-access` 真实浏览器**：完整流程 + 显式 UI 断言 + 成功截图落 `evidence/`；前端不做变异自检，信任锚点 = 截图 + 断言（避免前端假绿）。
- **RBT 风险驱动**：只覆盖高优先级跨层场景，砍低价值测试。
- **借 ln 理念、自包含实现**：参考 ln-520/523/404 思想，零插件耦合。

## 输入

```
vj-test epic-1     # 按 epic
vj-test            # 取最近执行的 epic
```

## 产出（都在 `docs/tasks/work/epic-{N}-{slug}/`）

- `_test-plan.md` — RBT 测试规划（场景 + 层 + 断言 + 优先级）
- `_test-report.md` — 人可读报告（覆盖/变异结果/截图链接/未覆盖项）
- `evidence/{scenario}-ok.png` — 前端 E2E 成功截图
- 测试代码文件（后端 pytest/httpx；前端经 web-access 驱动的流程脚本/断言）

## 文件

- `SKILL.md` — 5 Phase 工作流（探基建+起应用 → RBT 规划 → 写+跑 → 变异自检 → 报告）
- `README.md` — 本文件
