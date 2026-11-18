---
name: vj-mock-board
description: 根据产品需求文档（PRD）生成单文件 UI mock board（mock HTML）——解析 PRD 出 Screen Inventory，匹配 docs/project/DESIGN.md 双轨设计 token，按 Epic 分区平铺全部屏幕与关键状态，让用户在写代码前看到产品长什么样。用户说"出 mock""画个原型板""mock board""mock html""看看产品长什么样""PRD 转界面""UI mock""wireframe""mockup"时使用。缺 DESIGN.md 时先路由 vj-design-md-matcher；不用于实现期选风格，不产生产代码。
---

# vj-mock-board — PRD → 单文件 UI Mock Board

把 PRD 画成一张可浏览的单文件 mock board：按 Epic 分区平铺全部屏幕和关键状态，每屏附一个注记框，
写这块 UI 逼出来的 API 和设计决策。用途是在写代码前对齐产品长相，并反查接口和架构的遗漏——
注记框是板的核心价值，不是装饰。

不做：可点击的多页原型、React 或生产代码、更新 `docs/project/ui/surfaces.md`（那是 `vj-work`
做完计划后的事，计划可以引用板）、多方案风格探索（属 `vj-design-md-matcher`）、实现期使用（实现期以计划关键设计里的页面字段为准）。

## 产物

| 项 | 约定 |
|----|------|
| 板 | `docs/reference/research/designs/prd-{slug}/ui-mock-board.html`，单文件自包含 |
| 清单 | 同目录 `screen-inventory.md`，格式见 `references/screen-inventory.template.md` |
| 状态 | P0 屏（核心旅程）按必补清单（默认/加载/空/失败/禁用/完成/异常）画全；其余屏只画默认态 |
| 设备框 | 手机 390px 或桌面，按 PRD 使用场景定；不确定标 `⚠️ 推断` |

板是 PRD 的快照：板头写来源 PRD 版本和生成日期；它属于研究产物，不承载跨 Epic 合同。

## 约束（`scripts/validate_mock_board.py` 机检兜底）

- token 只来自 `docs/project/DESIGN.md`：正文颜色只用 `var(--token)`，`:root` 的值必须是 DESIGN.md 里的色值。
  屏型到轨道（front-of-house / operational）的判定按 `_shared/ui-planning-contract.md` §1。
- 单文件自包含：没有 CDN、外链字体或 `http(s)://` 资源，打开的人可能没网。
- 每屏必须有注记框。
- 机检不过就是没完成，不交付。

## 步骤

**P0 前置**：PRD 缺失就路由 `vj-product-requirements`（用户只给口头描述时可基于描述继续，全程标
`Confidence: L`）。`DESIGN.md` 缺失或明显过期就先路由 `vj-design-md-matcher`，有了再回来。
重跑时，若 `shasum <PRD> | cut -c1-16` 等于 `screen-inventory.md` 里记录的 PRD digest 且整板机检通过，
直接跳到 P5 并注明"PRD 未变"；不一致就只重生成受 PRD 改动影响的分区，新 digest 写回清单。

**P1 Screen Inventory**：按模板从 PRD 生成清单（屏名 / 来源条目 / 屏型 / 是否 P0 / 状态集 / 设备框 / 锚点 ID）。
屏的增删、屏型、P0 判定、设备框有多个合理选择时，合并成一次确认；无人值守时按最合理假设继续，
标 `⚠️ 推断 + Confidence`，板头写"清单假设待审批"。超过 20 屏时提示裁剪；无人值守就裁到核心旅程屏并在板头注明。
PRD 没有 Epic 结构时按用户旅程聚类分区，标 `⚠️ 推断`。
PRD 头部链接了场景原型（`vj-product-requirements` 第 4 步产出）时，屏幕和流程以原型为结构参考；原型只是临时视觉，
本板负责用正式 DESIGN.md 把所有屏幕画全。

**P2 骨架 + golden 屏**：按 `references/board-skeleton.md` 从 DESIGN.md 抽双轨 token 编进 `:root`，写板头和
公共 CSS 类，然后精做 1 个 P0 屏作为视觉语法样板。用户在场时可以先请其快速看一眼。

**P3 分区**：屏数超过 6 时，按 `references/subagent-dispatch.md` 每个 Epic 派一个子代理生成分区片段，
只许用骨架公共类和 `var()` 颜色，不自造调色板；否则在主上下文顺序生成。

**P4 装配 + 机检**：

```bash
python3 .agents/skills/vj-mock-board/scripts/validate_mock_board.py \
  docs/reference/research/designs/prd-{slug}/ui-mock-board.html \
  --inventory docs/reference/research/designs/prd-{slug}/screen-inventory.md \
  --design docs/project/DESIGN.md
```

失败只重写出问题的分区；重写一次还失败就自己修。

**P5 收尾**：用 `web-access` 打开板，按分区截图，对同一批截图过一遍：不滥用渐变、不堆 emoji 项目符号、
状态可辨、不空屏，以及九维一致性（色彩、字体、间距、圆角、阴影、图标、
卡片、按钮层级、装饰；每屏实心 accent 不超过 1 个）。要改的就地改，再跑 P4。这一步是建议性的，P4 机检才是硬闸；
用户可说"跳过审查"或要求派一个不带上下文的子代理对截图深审。`web-access` 不可用就跳过，板头注明"未做浏览器视觉验证"。
最后报告产物绝对路径和打开方式。

`DESIGN.md` 缺失且 `vj-design-md-matcher` 跑不了（没网或用户拒绝）时，用 `--wireframe` 出中性灰线框板，
板头标"风格待 DESIGN.md 定稿后重染"。
