---
name: vj-mock-board
description: 根据产品需求文档（PRD）生成单文件 UI mock board（mock HTML）——解析 PRD 出 Screen Inventory，匹配 docs/project/DESIGN.md 双轨设计 token，按 Epic 分区平铺全部屏幕与关键状态，让用户在写代码前看到产品长什么样。用户说"出 mock""画个原型板""mock board""mock html""看看产品长什么样""PRD 转界面""UI mock""wireframe""mockup"时使用。缺 DESIGN.md 时先路由 vj-design-md-matcher；不用于实现期选风格，不产生产代码。
---

# vj-mock-board — PRD → 单文件 UI Mock Board

把 PRD 变成一张可浏览的单文件 mock board：按 Epic 分区平铺全部屏幕×关键状态，
每屏带"这块 UI 逼出来的 API/设计决策"注记，用于在动代码前对齐产品长相、反查接口与架构遗漏。

**工作流位置**：PRD 定稿后、`vj-epic-story` 之前；对已有 PRD 可随时跑。

```text
vj-product-requirements → vj-mock-board → vj-epic-story → vj-epic-plan → vj-work
                             ↑ 缺 DESIGN.md 时先路由 vj-design-md-matcher
```

## Boundary（适用 / 不适用）

做：
- 解析 PRD（EARS 条目 / 用户旅程 / NFR）→ Screen Inventory → 按 `docs/project/DESIGN.md`
  双轨 token 生成单文件 mock board（HTML）
- 产出是 **PRD 快照**：板头标注来源 PRD 版本 + 生成日期；PRD 变更后整板幂等重跑覆盖

不做：
- 不是可点击多页原型，不产 React/生产代码，不建前端工程
- 不更新 `docs/project/ui/surfaces.md`（那是 `vj-epic-plan` 的职责；它可反向引用板作结构参考）
- 不发明风格：token 唯一来源 `docs/project/DESIGN.md`，缺失/明显过期即路由
  `vj-design-md-matcher`，不临时自选
- 不在 `vj-work` / story 实现期使用（实现期以 `docs/project/ui/surfaces.md` Screen Contract 为准）
- 不做多方案/多保真度变体探索（方向探索属 `vj-design-md-matcher` 轨）

## 产物合同

| 项 | 约定 |
|----|------|
| 板 | `docs/reference/research/designs/prd-{slug}/ui-mock-board.html`（单文件自包含） |
| 清单 | 同目录 `screen-inventory.md`（机检输入 + 反查索引），格式见 `references/screen-inventory.template.md` |
| 分区 | 按 Epic 分区平铺；每屏 = 屏名 + 状态标签 + 注记框 |
| 状态粒度 | P0 屏（核心旅程）按 `ui-state-coverage` 必补清单画全；其余屏只画默认态 |
| 设备框 | 手机框 390px 或桌面框，按 PRD 使用场景判定；不确定标 `⚠️ 推断` 由 Inventory gate 定 |

## 铁律

- **token 唯一来源 `docs/project/DESIGN.md`**：正文颜色只允许 `var(--token)`；`:root` 变量值
  必须 ∈ DESIGN.md 色值集合（`scripts/validate_mock_board.py` 机检兜底）。屏型→轨道
  （front-of-house / operational）判定按 `.agents/skills/_shared/ui-planning-contract.md` §1
  执行，本 skill 不复述。
- **单文件自包含**：无 CDN、无外链字体、无 `http(s)://` 资源引用（机检兜底），
  不假设打开板的人有网络。
- **先 golden 屏定视觉语法，后批量**：骨架 + 1 个 P0 屏先行；分区 agent 只允许用骨架
  公共 CSS 类 + `var()` 颜色，不得自造调色板。
- **每屏必带注记框**（机检兜底）：写这块 UI 逼出来的 API / 设计决策，用于反查
  架构与接口设计遗漏——这是板的核心价值，不是装饰。
- **mock 不是合同**：板属研究产物（`docs/reference/research/`），不承载跨 Epic 稳定契约；
  推断出的屏型 / 分区 / 状态标 `⚠️ 推断`，由用户在 gate 确认。
- **机检不过 = 本 skill 未完成**，不得交付。

## 输入

```text
vj-mock-board                                    # 默认读 docs/project/requirements.md
vj-mock-board docs/project/requirements.md       # 指定 PRD 路径
vj-mock-board <PRD 路径> --wireframe             # 降级中性线框板（仅兜底场景，见失败表）
```

## 工作流（6 Phase）

### P0 前置检查

1. PRD 缺失 → 路由 `vj-product-requirements`；用户只给了口头描述 → 基于描述继续并全程标
   `Confidence: L`。
2. `docs/project/DESIGN.md` 缺失或明显过期（判定口径同 `vj-design-md-matcher` 触发条件）→
   先路由 `vj-design-md-matcher`，产出 DESIGN.md 后回到本流程。

### P1 Screen Inventory

按 `references/screen-inventory.template.md` 解析 PRD 生成清单表（屏名 / 来源条目 / 屏型 /
P0 判定 / 状态集 / 设备框 / 锚点 ID），写入产物目录的 `screen-inventory.md`。
**用户确认 gate**：屏的增删、屏型、P0 判定、设备框由用户拍板；
无人值守 → 按最合理假设继续，逐项标 `⚠️ 推断 + Confidence: H/M/L`，板头标"清单假设待审批"，
不阻塞、不静默拍板。

### P2 骨架 + golden 屏

按 `references/board-skeleton.md`：从 DESIGN.md 抽双轨 token 编译进板内 `:root`，
写板头（来源 PRD 版本 + 生成日期 + 用法说明）与公共 CSS 类，然后精做 1 个 P0 屏做
golden 样例定视觉语法。有用户在场可请其快看一眼 golden 屏；无人值守直接继续。

### P3 分区生成

按 `references/subagent-dispatch.md` 每 Epic 派一个 subagent 生成该分区 HTML 片段。
清单总屏数 ≤6 或无 subagent 能力时，降级为主上下文顺序生成（标注 "dispatch inline fallback"）。

### P4 装配 + 机检

拼装整板后跑：

```bash
python3 .agents/skills/vj-mock-board/scripts/validate_mock_board.py \
  docs/reference/research/designs/prd-{slug}/ui-mock-board.html \
  --inventory docs/reference/research/designs/prd-{slug}/screen-inventory.md \
  --design docs/project/DESIGN.md
```

exit != 0 → 对应分区回炉重写（不整板重跑）；回炉一次仍 fail → 主上下文亲自修该分区。

### P5 收尾

1. 用全局 `web-access` skill 打开板截图自查（富度 / 反 AI-slop：无渐变滥用、无 emoji
   项目符号堆砌、状态可辨）。
2. **后置审查钩子**：自动触发 `ui-visual-consistency-audit` 对板做视觉一致性审查并采纳修正；
   用户可说"跳过审查"。
3. 报告产物绝对路径 + 浏览器打开方式；提示下游：`vj-epic-story` 拆解时可引用板，
   `vj-epic-plan` 可将其登记为 Screen Contract 的 Design source。

## 失败模式与兜底

| 触发条件 | 一线修复 | 仍失败兜底 |
|----------|----------|------------|
| DESIGN.md 缺失且 `vj-design-md-matcher` 跑不了（无网络 / 用户明确拒绝） | 以 `--wireframe` 降级中性灰线框板，板头标"风格待 DESIGN.md 定稿后重染" | 交付线框板并在收尾报告中标注 |
| 清单屏数 >20 | 提示裁剪（P1 屏减态 / 只画核心 Epic），用户确认 | 无人值守自动裁到核心旅程屏，板头标注裁剪范围 + `⚠️ 推断` |
| 分区片段机检 fail | 该分区回炉一次 | 主上下文亲自修该分区 |
| `web-access` 不可用 | 跳过截图自查 | 板头标"未做浏览器视觉验证"，收尾报告注明 |
| PRD 无 Epic 结构（自由格式需求） | 按用户旅程聚类自建分区，标 `⚠️ 推断` | Inventory gate 让用户定分区 |
| 产物目录不可写 | 先创建目录再写 | 输出板全文到对话，请用户确认落盘路径 |

## Stop conditions

- Inventory 确认 gate 反馈 ≥3 轮不收敛 → 弹"继续（按当前清单出板）/ 重审 PRD / 放弃"，
  不进入死循环。

## 触发示例

- "根据 PRD 出一版 mock，看看产品长什么样"
- "把 requirements.md 画成界面 mock board"
- "PRD 更新了，重跑 mock board"
- "给这个需求出个 UI mock / wireframe / mockup"
