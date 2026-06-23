# DESIGN.md — vibejet 设计契约（单一真相源）

> 设计 token 的唯一来源。改设计先改本文件 → 同步编译进 `frontend/src/index.css` 的 CSS 变量
> (`@theme` + `:root`)。**组件里不写裸 hex / 裸间距**,只用语义 token。
> v0.1：由登录屏(front-of-house)初始化;后续屏型按需扩充 §Richness Floor / §Reference Skeletons。

## 方向（Direction）

- **气质**:Soft Structuralism（柔性结构主义）—— 中性近白底、克制 hairline、柔和扩散阴影、
  大号几何 grotesk 标题、组件轻盈悬浮。参考 Linear / Vercel / Mobbin 的克制高级感。
- **品牌色**:中性底 + 单一品牌强调色 = **靛蓝 → 紫 渐变**(冷静 + 科技活力)。强调色仅用于
  首要操作、链接、焦点环与品牌视觉锚;不做装饰性滥用(每屏实心 accent 按钮 ≤ 1)。
- **字体**:`Geist`(UI/正文/标题)、`Geist Mono`(数字/ID/时间)。**禁用** Inter/Roboto/Arial/Helvetica。

## 调色板（Color Tokens）

语义 token（light，默认）。值见 `index.css` 的 `:root`;此处为契约说明。

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
| `--brand-from / via / to` | `#4F46E5 / #7C3AED / #A855F7` | 品牌渐变(右侧面板) |

- **状态表达 = 颜色 + 图标 + 文案**三件套,不只靠颜色(无障碍)。
- 提供 `.dark` token 组(同形,完整起见);本期登录默认 light,无主题切换。

## 字阶（Type Scale）

每屏字号 ≤ 4 档。`font-sans` = Geist。

| 角色 | size / weight / 行高 | 备注 |
|---|---|---|
| Display(登录大标题) | `text-3xl`(30px) ~ `text-4xl`(36px) / 700 / 1.1 | 紧字距 `tracking-tight` |
| Slogan(右侧) | `text-3xl`~`text-4xl` / 600 / 1.15 | 白色,落在渐变上 |
| Body | `text-sm`(14px) / 400–500 | 表单、说明 |
| Subtle | `text-xs`(12px) / 400 | 法务小字、辅助 |
| Numeric | Geist Mono,数字右对齐 | 金额/ID/时间 |

## 圆角（Radius）

- 基准 `--radius: 0.75rem`(12px);派生 `sm/md/lg/xl`(见 index.css)。
- 输入/卡片用 `lg`;大容器/右侧面板用 `xl`+;按钮用 `lg`(squircle 感,非全 pill)。
- 双层卡片(Doppelrand)时内核半径 = 外壳半径 − padding,保持同心曲率。

## 间距层级（Spacing Hierarchy）

数值唯一来源。全屏 gap/padding ≤ 4 种,全部 4px 刻度。**页框必须呼吸,密度只压数据核心。**

| 层 | 范围 | 本期登录用法 |
|---|---|---|
| 页级 padding | `px-6`~`px-10` / `py-10`~`py-16` | 左认证面板列的外边距 |
| 区块间 gap | `gap-8`~`gap-10` | logo↔标题↔表单↔页脚 之间 |
| 容器内 padding | `p-6`~`p-8` | 卡片/分组 |
| 组件内节奏 | `gap-2`~`gap-4` | label↔input、字段间、按钮内 |

## 组件规则（Component Rules）

- **按钮**:首要 = 实心 primary,`rounded-lg`、`px-5 py-2.5`、`active:scale-[0.98]`、
  过渡用 `ease-[cubic-bezier(0.32,0.72,0,1)] duration-300`。次要 = secondary/ghost。每屏实心 accent ≤ 1。
- **输入**:label 在上(必填加 `*` + `aria-required`),错误文案在字段下方(destructive 色 + 文案)。
  焦点 `focus-visible` 环用 `--ring`。
- **图标**:lucide-react,`strokeWidth={1.5}`(精细线条)。
- **阴影**:柔和扩散环境阴影(如 `shadow-[0_8px_30px_rgba(16,16,40,0.06)]`),禁生硬黑投影。
- **三态**:加载(按钮内 spinner + 禁用 / `SuspenseLoader` 骨架);空(图标+说明+引导);
  错误(原因 + 重试 / `sonner` toast,语义色)。

## Richness Floor（富度地板）

| 屏型 | 默认组成(地板) |
|---|---|
| **front-of-house**(login/landing) | 产品身份(logo/wordmark)+ 版面结构(分栏/居中)+ 清晰层次(标题/副标题/操作)+ 视觉锚(品牌渐变/图形)+ 三态。**不做 AC 最小薄屏**(不许塌成一个居中裸卡)。 |

## Reference Skeletons（参考骨架）

### login（front-of-house · Editorial Split）

```
┌───────────────────────────┬───────────────────────────────┐
│  左：认证面板 (居中列 max-w-sm) │  右：品牌渐变面板 (hidden lg:block) │
│   · wordmark / logo          │   · indigo→violet mesh 渐变      │
│   · H1 大标题 + 副标题         │   · 发光球 + 细网格/噪点          │
│   · LoginForm(用户名/邮箱+密码) │   · 大号 slogan(白)             │
│   · 主按钮(primary, 全宽)      │   · 底部小字 footnote(可选)       │
│   · 页脚:法务小字 + 注册占位链接 │                                │
└───────────────────────────┴───────────────────────────────┘
```
- 移动端(`< lg`):右栏隐藏,左认证面板全宽居中,`px-4 py-8`,`min-h-[100dvh]`。
- 字号 ≤ 4 档;间距 ≤ 4 种;accent 实心按钮 = 1(登录)。

## Slogan（占位,可改）

- 主 slogan(右侧):**“Build at the speed of thought.”**（或中文“以思维的速度构建。”)
- 副标题(左侧标题下):“登录以继续 vibejet。”

> 出口闸(A 轨):实现后桌面+移动截图,与一个同类高级登录参考并排对照版面/层次,过三问再标 done。
