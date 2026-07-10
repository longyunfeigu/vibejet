# Screen Inventory 模板（P1 产物）

写入 `docs/reference/research/designs/prd-{slug}/screen-inventory.md`。
它同时是 P4 机检（`validate_mock_board.py --inventory`）的输入和板的反查索引，
表格结构不得增删列（机检按列名解析）。

## 文件结构

```markdown
# Screen Inventory — {产品名}

- 来源 PRD: {路径}（版本 {vX.Y}，{PRD 最后更新日期}）
- 生成日期: {YYYY-MM-DD}
- 确认状态: 已确认 | 假设待审批（无人值守时）

| 屏名 | 来源条目 | 屏型 | P0 | 状态集 | 设备框 | 锚点 |
|------|----------|------|----|--------|--------|------|
| 登录 | NFR 5.3 | front-of-house | ✅ | 默认, 提交中, 失败 | phone | s-login, s-login--loading, s-login--error |
| 今日总览 | E2 R2/R4 | operational | ✅ | 默认, 空, 加载 | phone | s-home, s-home--empty, s-home--loading |
| 目标设置 | E3 R1 | operational ⚠️ 推断 | — | 默认 | phone | s-goal |
```

## 各列派生规则

| 列 | 规则 |
|----|------|
| 屏名 | 从 PRD 的 EARS 条目 / 用户旅程 / Scenario 派生；一屏承载一个 Primary Job，不按技术组件拆屏 |
| 来源条目 | PRD 中逼出这块屏的条目索引（如 `E1 R3`、`NFR 5.3`）；一屏可对应多条 |
| 屏型 | `front-of-house / operational / mixed`，判定按 `.agents/skills/_shared/ui-planning-contract.md` §1，本模板不复述；不确定标 `⚠️ 推断` |
| P0 | 屏在 PRD 核心用户旅程（主流程 mermaid / 成功指标直接相关）上 → ✅；其余 `—` |
| 状态集 | P0 屏：按 `ui-state-coverage` 的"必须补齐"清单（默认/加载/空/失败/禁用/完成/异常）对照 PRD 逐项取舍，PRD 点名的分支态（如"无法识别""服务不可用"）必收；非 P0 屏：只写 `默认` |
| 设备框 | `phone`（390px）/ `desktop`，按 PRD 使用场景（目标用户的设备上下文）判定；不确定标 `⚠️ 推断` |
| 锚点 | 逗号分隔的 DOM id：默认态 `s-{slug}`，状态变体 `s-{slug}--{state-slug}`；slug 用小写英文短横线，一板内唯一 |

分区归属：每屏归属它来源条目所在的 Epic 分区；PRD 无 Epic 结构时按用户旅程聚类自建分区
并标 `⚠️ 推断`。跨 Epic 复用的屏（如全局导航壳）归首个引用它的分区，其余分区注记框内引用。

## 确认 gate 话术

一次性列出全表 + 待拍板项（屏的增删 / 屏型 / P0 / 设备框 / 分区归属），让用户批量确认，
不逐屏追问。无人值守 fallback 与 stop condition 见 `SKILL.md`（P1 与 Stop conditions 节），
本模板不复述。
