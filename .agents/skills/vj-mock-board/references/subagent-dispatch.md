# 分区 subagent 派发（P3）

每个 Epic 分区一个 subagent，并行派发。总屏数 ≤6 或无 subagent 能力 → 主上下文按同一
prompt 顺序生成各分区，收尾报告标注 "dispatch inline fallback"。

## 派发前提（P2 已就绪）

- 骨架已写盘（含 `:root`、公共类、视觉系统声明注释、golden 屏）
- `screen-inventory.md` 已过确认 gate（或已标"假设待审批"）

## Subagent prompt 模板

```text
你在为 mock board 生成一个 Epic 分区的 HTML 片段。这是纯静态 mock，不是生产代码。

【产出物】只输出一个 <section id="epic-{N}" class="epic-section">…</section> 片段，
不含 <html>/<head>/<style>，不写解释文字。

【样式合同（违反即返工）】
1. 只使用下列公共 CSS 类：{骨架类清单，含追加类}
2. 颜色只允许 var(--token)；禁止裸 hex / rgb / hsl / 新增 <style>
3. 片段内允许内联 style 做布局微调（间距/对齐），颜色仍只能 var()
4. 屏卡结构、锚点 id、注记框写法照抄 golden 屏范本（见下）

【视觉语法范本（逐条遵循其视觉系统声明）】
{golden 屏完整 HTML + 骨架顶部视觉系统声明注释}

【本分区清单（每行一卡，锚点 id 必须一致）】
{screen-inventory.md 中属于本 Epic 的行}

【PRD 依据（UI 内容与状态的唯一事实源，不得自行发挥需求）】
{PRD 中本 Epic 的条目原文 + 相关 NFR}

【每屏要求】
- 屏型决定用哪轨 token（front-of-house 用 --paper/--ink 系；operational 用 --background/--primary 系）
- 默认态卡必带 .note 注记框：写这块 UI 逼出来的 API（端点/关键字段/异常码）与设计决策
  （含被 PRD 条目约束的取舍），要具体可反查，不写空话
- 状态变体卡只改屏内呈现；状态表达用 颜色+图标+文案 三件套，不靠纯文案
- mock 数据用贴近真实的中文假数据（菜名/数值/时间），不用 lorem / Item 1
```

## 装配（P4 前置）

1. 按 Epic 编号顺序拼接各分区片段进骨架的分区占位处。
2. 拼接后全板锚点 id 去重检查（跨分区撞 id → 以 inventory 为准修正撞的一方）。
3. 跑机检（命令见 `SKILL.md` P4）。单分区 fail 只回炉该分区：把机检输出的违规项
   附进原 prompt 重派；回炉一次仍 fail → 主上下文亲自修。
