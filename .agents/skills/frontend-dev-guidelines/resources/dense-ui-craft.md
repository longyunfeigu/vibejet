# Dense-UI Craft — operational 屏的工艺标准

> 填补 B 轨的品味真空：`design-taste-frontend` 对 dashboards/admin out-of-scope，本文是
> operational 屏（dashboard / table-list / 审核台 / detail / form / 设置）的 craft 真相源。
> 蒸馏自 Linear / Airtable 这类"密而高级"的后台。数值硬范围以 `docs/project/DESIGN.md`
> §Spacing Hierarchy 为准；出口闸（C1–C5 / B1–B5）见 `.claude/rules/frontend.md`。
>
> 核心认知：**Linear 的高级感不是来自"密"，而是来自"密度有层级"。** 数据核心 8–12px 节奏，
> 但页面框架 24–32px 呼吸。全屏一个间距值（无论大小）= 没有设计。

## 1. 间距：核心密，框架透

- 心智模型：屏 = **页框 → 区块 → 容器 → 组件** 四层，间距逐层递减（24–32 → 16–24 → 16–20 → 8–12）。
  违规的两个方向同罪：页框用 8px（挤死）、组件内用 24px（散架）。
- 页头（标题 + 操作）周围是全屏最大的呼吸位：上下各 24–32，标题与副述之间 4–8。
- 区块之间优先用 **gap 留白** 分隔，其次才是边框；两者同时用 = 双重分隔，删一个。
- 自检手法：截图后横向扫一遍，应能看出 3 层明显不同的间距节奏；只看出 1 层 = 重修。

```tsx
// table-list 骨架的间距层级（数值取自 DESIGN.md §Spacing Hierarchy）
<div className="px-8 py-6">              {/* 页框 24–32 */}
  <header className="mb-6">…</header>    {/* 区块间 16–24 */}
  <section className="mb-5 …">统计带</section>
  <div className="mb-4 flex gap-2 …">工具条（组件内 8–12）</div>
  <Table>…行高 36–40px、单元格 px-3 py-2…</Table>
</div>
```

## 2. 层次：字重与色阶，不是字号

- 一屏字号 ≤ 4 档（从 DESIGN.md 字阶表取，operational 常用：22 页标题 / 14 正文 / 13 表格 / 12 caption）。
- 同一字号内做层次：**字重**（600 标题 / 500 标签 / 400 正文）×
  **文字色阶**（`text-primary` 关键值 → `text-secondary` 正文 → `text-tertiary` 元数据 → `text-disabled` 时间戳）。
  Linear 的密表可读，靠的就是 4 级文字色阶，不是字号跳跃。
- 数值/ID/时间戳一律 mono + 数字右对齐（`tabular-nums`）；表头 12–13px、`text-tertiary`、不加粗到 600。

## 3. 分区：色块优先，边框克制

- "borders not shadows" ≠ 处处加框。分区优先级：**留白 > `--surface` 色块 > 1px 单边框**。
- 禁止卡内嵌卡（Card 里再放带边框的 Card）：内层改用 `bg-surface` 色块或仅留分隔线。
- 表头、侧栏、代码块用 `--surface` 着色即可成区，不需要再包一层边框。
- 同屏边框种类 ≤ 2（如 `border-subtle` 行分隔 + `border-default` 容器）；第三种出现时先怀疑结构。

## 4. 对齐：一条左轨

- 全屏内容左缘对齐到**同一条垂直轨**：页标题、统计带、工具条、表格首列共享一条左线。
  截图画一条竖线验证——有元素游离在轨外（多 4px 都算）就修。
- 行内元素基线对齐；图标与文字用 `items-center` + 固定尺寸（`size-4`），不靠 margin 微调。
- 表格列：文本左对齐、数值右对齐、状态列固定窄宽；列宽给 meta 优先级（状态/标识/关键指标在前）。

## 5. 微态：hover 是密屏的呼吸阀

密屏靠交互微态补足信息分层，这是"高级感"的隐性来源：

- 行 hover：`hover:bg-surface`（已是 DESIGN.md 表格规则）；行操作默认弱化、hover 浮现（opacity 或显隐）。
- 可点击的一切有 `cursor-pointer` + hover 反馈 + `focus-visible` 环；可编辑单元格 hover 出铅笔（Airtable 范式）。
- 过渡统一 `transition-colors duration-150`；不做 transform 弹跳（operational 屏要稳）。

## 6. 克制：accent 是预算不是调料

- 每屏实心 accent 按钮 ≤ 1（首要操作）；次操作 secondary/ghost。
- 色相只表状态（success/warning/danger/info/ai）；一屏无异常时应近乎单色——彩色 pill 超过两种色相时检查是否把装饰当了状态。
- 图标默认 `text-tertiary`，不跟随 accent；选中态才用 accent。

## 反模式速查（"像 Excel"的特征）

| 反模式 | 修法 |
|---|---|
| 全屏 wall-to-wall 同一间距 | 按四层间距重排（§1） |
| 每个单元格/容器都有边框 | 删内框，改色块或行分隔线（§3） |
| 全文同字号同字重，靠加粗大写喊话 | 字重 × 色阶做层次（§2） |
| 无 hover / 行操作永远全亮 | 加微态，行操作 hover 浮现（§5） |
| 主按钮、链接、徽章、图标全是 accent | accent 预算 ≤1，余者降级（§6） |
| 标题/工具条/表格左缘错位 | 对齐到一条左轨（§4） |
