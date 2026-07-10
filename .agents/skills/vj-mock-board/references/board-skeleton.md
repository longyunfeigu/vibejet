# Board 骨架规范（P2 产物）

骨架 = 板头 + `:root` token 块 + 公共 CSS 类 + Epic 分区占位 + 1 个 golden 屏。
骨架是分区 subagent 的唯一样式合同：分区片段只允许用这里定义的类 + `var()` 颜色。

## 板头（必填）

```html
<header class="board-head">
  <h1>{产品名} · UI Mock Board</h1>
  <p>来源: {PRD 路径}（{vX.Y}）· 生成: {YYYY-MM-DD} · 由 vj-mock-board 生成，PRD 变更后整板重跑</p>
  <p>用法: 每屏下方注记框是这块 UI 逼出来的后端 API / 设计决策——用于反查架构与接口设计的遗漏。</p>
  <!-- 按需追加状态行: 清单假设待审批 / 已裁剪范围 / 风格待 DESIGN.md 定稿后重染 / 未做浏览器视觉验证 -->
</header>
```

## `:root` token 编译规则

- 从 `docs/project/DESIGN.md` 的调色板表格抽取，**逐值照抄不改造**（机检：`:root` 内
  每个色值必须 ∈ DESIGN.md 色值集合）。
- 双轨都编译进来：operational 轨（`--background`、`--primary` 等）+ front-of-house 轨
  （`--paper`、`--ink` 等），变量名沿用 DESIGN.md 原名。屏按自己的屏型取对应轨的变量。
- 只出 light（operational 轨的 `.dark` 组不编译；front-of-house 轨本身 light-only）。
- 字体：mock 板不引外链/自托管字体文件，`font-family` 按 DESIGN.md 声明族名 +
  系统回退栈（如 `"Noto Sans SC", -apple-system, sans-serif`）；用户机器缺字体时
  降级到系统字体是可接受的 mock 保真度。
- **`--wireframe` 降级模式**（仅失败兜底）：`:root` 只允许灰阶（`#000`–`#fff` 等 R=G=B 值），
  机检以 `--wireframe` flag 放行灰阶、跳过 DESIGN.md 比对。

## 公共 CSS 类（样式合同）

骨架内定义、板内通用，类名固定（机检与 subagent 合同都依赖）：

| 类 | 用途 |
|----|------|
| `.board` | 分区容器：flex 换行平铺屏卡 |
| `.screen-card` | 一屏一状态的外层卡（含锚点 id）；内含设备框 + 状态标签 + 注记框 |
| `.phone` / `.desktop` | 设备框：phone 390px 圆角描边；desktop 960px 浏览器框 |
| `.state-tag` | 状态标签（默认/加载/失败…），放屏名旁 |
| `.note` | 注记框（虚线框），每屏默认态卡内必有（机检兜底） |
| `.epic-title` / `.epic-sub` | 分区标题 + 来源条目索引行 |

以上之外允许骨架按产品需要**追加**少量公共类（如进度条、日历格），一并写进骨架并列入
subagent 输入的类清单；分区片段内**不得**新增 `<style>` 或内联定义新调色板。
片段内允许内联 `style` 做布局微调（间距/对齐），但颜色值只能 `var()`。

## 屏卡结构（golden 屏即此结构的精做示范）

```html
<section id="epic-1" class="epic-section">
  <h2 class="epic-title">Ⅰ · {Epic 名}</h2>
  <div class="epic-sub">{来源条目索引，如 E1 R1–R6}</div>
  <div class="board">

    <div class="screen-card" id="s-record">
      <div class="phone"><!-- 屏内容：本屏默认态 UI --></div>
      <div class="screen-meta">{屏名} <span class="state-tag">默认</span></div>
      <div class="note">
        <b>API:</b> POST /api/v1/meals/recognize（10s 超时 → 服务不可用态）<br>
        <b>决策:</b> 默认态不出现文本输入框（PRD R3：文本仅兜底）
      </div>
    </div>

    <div class="screen-card" id="s-record--loading">
      <div class="phone"><!-- 同屏加载态 --></div>
      <div class="screen-meta">{屏名} <span class="state-tag">识别中</span></div>
      <!-- 状态变体卡可无 note；该屏的 note 住默认态卡 -->
    </div>

  </div>
</section>
```

- 锚点 id 与 `screen-inventory.md` 锚点列一一对应（机检兜底）。
- 注记框内容要具体到"端点/字段/状态码/取舍"，能反查出遗漏；不写"需要后端支持"这类空话。
- 状态变体卡只改屏内 UI 呈现，不复制注记框（一屏一份，住默认态卡）。

## Golden 屏要求

- 选 P0 屏中状态最多的一屏精做（含其全部状态变体卡），作为分区 subagent 的抄写范本。
- 落笔前先在骨架顶部 HTML 注释里声明视觉系统（轨道、层级手法、间距节奏、状态表达三件套：
  颜色+图标+文案），分区片段遵循同一声明。
- 富度地板：状态可辨（不靠纯文案）、不空屏、失败态给出下一步动作入口；
  反 AI-slop：无装饰性渐变、无 emoji 项目符号堆砌、颜色只表状态与首要操作。
