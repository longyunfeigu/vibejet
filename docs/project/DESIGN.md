# DESIGN.md — vibejet 设计契约（单一真相源）

> 设计 token 的唯一来源。改设计先改本文件 → 同步编译进 `frontend/src/index.css` 的 CSS 变量
> (`@theme` + `:root`)。**组件里不写裸 hex / 裸间距**,只用语义 token。
> v0.2：login 屏采用「编辑艺术」方向后更新；operational 屏仍走原中性系。

## 方向（Direction）

设计分两轨，共享同一套 token 文件：

- **front-of-house**（login / landing / 空首屏）: **编辑艺术（Editorial Art）**——纸色底、
  衬线排印（思源宋标题 + Instrument Serif 斜体 wordmark）、下划线式输入、墨绿单强调色、
  画廊式装裱画作视觉锚。参考 Mercury / 印刷品 / 画廊标签的气质：往界面里借印刷与艺术的势。
- **operational**（dashboard / table / form / 设置）: 中性近白底 + 克制 hairline + 单一靛蓝
  强调（Soft Structuralism），参考 Linear / Vercel 的克制。密度与工艺规则见
  `.claude/rules/frontend.md` C1–C5。
- 强调色纪律（两轨通用）：每屏实心 accent 按钮 ≤ 1；颜色只表状态与首要操作，不做装饰。

## 字体（Fonts）

- UI/正文: `Geist`（Latin）+ `Noto Sans SC`（CJK 回退）
- 数字/ID/时间: `Geist Mono`，数字右对齐
- 编辑排印标题（front-of-house）: `Noto Serif SC`（`--font-serif`）
- 展示衬线 wordmark/引文（front-of-house）: `Instrument Serif` italic（`--font-display`）
- **禁用** Inter/Roboto/Arial/Helvetica

## 调色板（Color Tokens）

### 全局 UI 系（operational 屏，light 默认，`.dark` 有对应组）

| Token | 值(light) | 用途 |
|---|---|---|
| `--background` | `#FBFBFD` | 页面底色(冷调近白) |
| `--foreground` | `#0B0B12` | 主文本 |
| `--card` / `--popover` | `#FFFFFF` | 卡片/浮层底 |
| `--muted` | `#F4F4F7` | 次级面块底(分隔/hover) |
| `--muted-foreground` | `#71717A` | 副标题/占位/弱文本 |
| `--primary` | `#5046E5` | 品牌强调(首要按钮、链接) |
| `--primary-foreground` | `#FFFFFF` | 强调上的文字 |
| `--secondary` | `#F4F4F7` | 次级按钮底 |
| `--accent` | `#EEEDFE` | 极淡靛紫 hover 面 |
| `--accent-foreground` | `#4338CA` | accent 面上的文字 |
| `--border` | `#ECECF1` | hairline 边框 |
| `--input` | `#E6E6EC` | 输入边框 |
| `--ring` | `#5046E5` | 焦点环(= primary) |
| `--destructive` | `#E5484D` | 错误/危险 |
| `--success` | `#16A34A` | 成功 |
| `--warning` | `#D97706` | 警告 |
| `--brand-from / via / to` | `#4F46E5 / #7C3AED / #A855F7` | 品牌渐变(AppShell wordmark) |

### 编辑艺术系（front-of-house 屏，light-only，不随 `.dark` 翻转）

| Token | 值 | 用途 |
|---|---|---|
| `--paper` | `#FAF9F6` | 纸色页面底 |
| `--ink` | `#1C1B17` | 主文本/聚焦下划线 |
| `--ink-muted` | `#75726A` | 副标题/正文弱化 |
| `--ink-faint` | `#8F8C81` | 表单小标签/分隔符文字/画作标签 |
| `--ink-ghost` | `#A5A296` | 页脚法务/占位符/斜体注 |
| `--line` | `#D9D5C9` | hairline(输入下划线/按钮描边/链接下划线) |
| `--line-soft` | `#E2DED2` | 更淡的分隔线 |
| `--pine` | `#21382C` | 首要操作(墨绿实心按钮)/链接 |
| `--pine-deep` | `#1A2E24` | pine hover |
| `--cream` | `#F5F2E8` | pine 上的文字 |

- 画作本体（BrandPanel 月夜图的渐变/月色）视为**插画资产的颜料**，允许 inline 值，不 token 化。
- **状态表达 = 颜色 + 图标 + 文案**三件套,不只靠颜色(无障碍)。

## 字阶（Type Scale）

每屏字号 ≤ 4 档。

| 角色 | size / weight / 行高 | 备注 |
|---|---|---|
| Display(登录大标题) | `40px` / 600 / 1.2 | `--font-serif`,字距 `+0.01em` |
| Wordmark | `26px` italic | `--font-display` |
| Body | `14–15px` / 400–500 | 表单、说明 |
| Subtle | `12px` / 400 | 法务小字、表单小标签(标签加宽字距 `0.32em`) |
| Numeric | Geist Mono,数字右对齐 | 金额/ID/时间 |

## 圆角（Radius）

- 基准 `--radius: 0.75rem`(12px);派生 `sm/md/lg/xl`(见 index.css)。
- operational: 输入/卡片用 `lg`;大容器用 `xl`+;按钮用 `lg`。
- front-of-house 编辑系: 按钮 `10px`;输入**无圆角**(下划线式);装裱画 `2px`。

## 间距层级（Spacing Hierarchy）

数值唯一来源。全屏 gap/padding ≤ 4 种,全部 4px 刻度。**页框必须呼吸,密度只压数据核心。**

| 层 | 范围 | 本期登录用法 |
|---|---|---|
| 页级 padding | `px-6`~`px-20` / `py-10`~`py-14` | 左认证列外边距;画作装裱边 `inset-7` |
| 区块间 gap | `gap-8`~`gap-12` | 标题↔社交↔表单↔链接行 之间 |
| 容器内 padding | `p-6`~`p-8` | 卡片/分组 |
| 组件内节奏 | `gap-1`~`gap-4` | label↔input、字段间、按钮内 |

## 组件规则（Component Rules）

- **按钮**:首要 = 实心(`--pine`(front-of-house) / `--primary`(operational)),
  `active:scale-[0.99]`,过渡 `ease-[cubic-bezier(0.32,0.72,0,1)] duration-300`。
  次要 = hairline 描边。每屏实心 accent ≤ 1。
- **输入**(front-of-house):下划线式——`border-b` `--line`,无圆角无底色,label 在上
  (小字加宽字距),聚焦时下划线转 `--ink` 并以 `box-shadow` 加重 1px(不产生布局跳动);
  错误文案在字段下方(destructive 色)。operational 屏维持描边输入 + `--ring` 焦点环。
- **图标**:lucide-react,`strokeWidth={1.5}`。
- **纹理**:胶片颗粒用 `bg-grain` utility(SVG feTurbulence)+ `mix-blend-overlay`,仅用于画作。
- **三态**:加载(按钮内 spinner + 禁用 / `SuspenseLoader` 骨架);空(图标+说明+引导);
  错误(原因 + 重试 / `sonner` toast,语义色)。

## Richness Floor（富度地板）

| 屏型 | 默认组成(地板) |
|---|---|
| **front-of-house**(login/landing) | 产品身份(衬线 wordmark)+ 版面结构(编辑分栏)+ 清晰层次(衬线标题/副标题/操作)+ 视觉锚(装裱画作 + 画廊标签)+ 三态。**不做 AC 最小薄屏**(不许塌成一个居中裸卡)。 |

## Reference Skeletons（参考骨架）

### login（front-of-house · Editorial Art）

```
┌─────────────────────────────┬───────────────────────────────┐
│  左：认证列 46% (纸色 --paper)  │  右：画廊面板 54% (hidden lg)     │
│   · wordmark: Instrument     │   · 画作装裱在纸色留边内(inset-7)  │
│     Serif italic "vibejet"   │   · CSS 月夜画(渐变海平线+月亮+    │
│   · H1 衬线大标题「欢迎回来。」  │     倒影+bg-grain 颗粒)          │
│   · 社交登录(条件显示)+ 分隔线   │   · 左下:画廊式作品标签           │
│   · 下划线式表单 + 墨绿主按钮    │     《想法，即产品》no.01 —       │
│   · 注册/忘记密码 下划线链接行   │     vibejet studio, 2026        │
│   · 页脚:© + 条款/隐私        │                                │
└─────────────────────────────┴───────────────────────────────┘
```
- 移动端(`< lg`):右栏隐藏,左认证列全宽,`px-6`,`min-h-[100dvh]`。
- 字号 ≤ 4 档;间距 ≤ 4 种;accent 实心按钮 = 1(登录, `--pine`)。

## 作品标题（画作/Slogan）

- 右侧画作标题:**《想法，即产品》**(画廊标签体例:标题 + 编号 + 落款)
- 副标题(左侧标题下):「登录以继续你的构建。」

> 出口闸(A 轨):实现后桌面+移动截图,与一个同类高级登录参考并排对照版面/层次,过三问再标 done。
