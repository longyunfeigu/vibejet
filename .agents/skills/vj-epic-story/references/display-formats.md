# vj-epic-story 展示格式模板

SKILL.md 各 Phase 的用户交互展示格式集中在此，按需读取。规则语义不在本文件——
这里只是"长什么样"，判定规则以 SKILL.md 与 `scripts/validate_story.py` 为准。

## §A Phase 2.3 — Epic 差异分析

```
📋 Epic 差异分析

✅ KEEP (N 个): 无变化
- Epic 1: 用户管理
- Epic 2: 商品目录

🔧 UPDATE (M 个): 范围/标准已变
- Epic 3: 订单
  diff: 新增"退款流程"（来源 PRD R12-R14），原"售后客服"已移至 Epic 5

❌ OBSOLETE (K 个): 不再在当前需求范围内
- Epic 4: 短信验证码 → 建议归档（已被第三方 SDK 替代）
  ⚠️ 该 Epic 有 2 个 Story 状态为 in_progress，归档需人工评估

➕ CREATE (L 个): 新增
- Epic 6: 数据分析（来源 PRD R15-R18，新需求）

请审核差异：输入 confirm 接受 / 输入 adjust 调整 / 输入 abandon 放弃
```

## §B Phase 2.5 — Epic Quality Gate 体检结果

```
📋 Epic Quality Gate 体检结果

Epic 1: 用户管理
  ✓ Scope clarity
  ✓ Balance (5 Requirements，均值 6)
  ✓ Independence
  得分: 3/3 PASS

Epic 2: 商品目录
  ⚠️ Scope clarity
     问题: In Scope 与 Epic 1 有 ~40% 重叠（账号相关功能）
     建议: 把"账号设置"归并到 Epic 1，Epic 2 只留商品目录
  ✓ Balance
  ✓ Independence
  得分: 2/3 WARNING

Epic 3: ...

总分: 17/18 (1 个 Epic 有警告)
输入 continue 接受警告 / 输入 fix 修订 / 输入 rework 回到 Phase 2.1
```

## §C Phase 2.6 Step 4 — Batch Question 大表

```
📋 Epic 详情自动填充结果（请一次性补齐 ❓ 和确认 ⚠️）

═══════════════════════════════════════
Epic 1: 用户管理
═══════════════════════════════════════
  ✓ 业务目标: 让新用户能注册登录找回密码（来源: PRD §11.1）
  ✓ In Scope: 手机号注册、手机号登录、密码重置（PRD R1-R5）
  ⚠️ Out of Scope: 第三方登录（推断自 PRD §9 "未来版本"，请确认）

  用户旅程:
  ⚠️ 主旅程: 访问注册页 → 输入手机号 → 收验证码 → 设置密码 → 注册成功跳转首页（推断自 PRD R1-R5，请确认）
  ❓ 异常旅程: 验证码错误 / 短信失败 / 手机号已注册的系统响应未知，请补齐
  ⚠️ 页面体验地图: 注册页主操作为"创建账号"，次操作为"已有账号去登录"；错误提示不只依赖 toast（推断，请确认）

  System-Wide:
  ✓ 跨模块影响: 牵动 Epic 3 订单（需要 user_id）→ 建议 Epic 1 先交付
  ✓ 不变量保护: 用户名唯一性约束 → 加入 Story 1.1 的 Edge AC
  ❓ 状态生命周期: session 过期策略未知，请确认（24h / 7d / 配置化？）
  ✓ API 表面一致性: /api/users 已存在，新增字段需 minor 版本号
  ⚠️ 错误传播: 短信失败时降级到邮件（推断，请确认）
  ✓ 权限边界: 仅限本人修改个人资料

═══════════════════════════════════════
Epic 2: 商品目录
═══════════════════════════════════════
  ...

请按 Epic 编号逐项补齐 ❓ 和回应 ⚠️，或直接输入 confirm 接受所有 ⚠️
```

## §D Phase 5.2 — 写盘前批量预览

```
📋 完整产出预览（共 N 个 Epic, M 个 Story）

═══════════════════════════════════════
Epic 1: 用户管理 (P0, 5 Story, 平铺模式)
═══════════════════════════════════════
[Epic 概述]: 让新用户能注册登录找回密码
[用户旅程]: 主旅程 5 步；异常旅程 4 条；全部已映射到 Story/AC
[页面体验地图]: 2 个页面/区域；主操作、关键状态、体验护栏已覆盖
[System-Wide]: 已识别 6 项（4 进 AC，1 路由 PRD open questions，1 由 repo 基线承载）

Story 1.1: 手机号注册 (US001)
  Happy: 1 | Edge: 2 | Error: 2 | Integration: 0 | FE: 2 | Assumptions: 1
Story 1.2: 手机号登录 (US002)
  Happy: 1 | Edge: 1 | Error: 2 | Integration: 0 | FE: 2 | Assumptions: 0
Story 1.3: 密码重置 (US003)
  ...

═══════════════════════════════════════
Epic 2: 商品目录 (P0, 4 Story, 展开模式)
═══════════════════════════════════════
...

───────────────────────────────────────
完整性验证（先于写盘）:
  ✅ 所有 PRD 需求都有 Story 映射
  ✅ EARS 反向追溯：每条 If-Then/While 子句都映射到 Error/Edge AC
  ✅ 旅程完整性：用户旅程 section 存在；主旅程每步都有 Story；异常旅程都有 Story/AC
  ✅ 前端体验完整性：前端 Epic 有页面体验地图；UI Story 都映射到页面/区域；控件细节只出现在前端 AC
  ✅ INVEST 检查通过
  ✅ validate_story.py 机检通过（AC≤7 / 验证三要素 / Assumptions / 无 Bundling / 无前向依赖）
  ✅ Quality Gate Balance 复检：Story 数 [5,4,6,3,5]，方差正常

写盘后改动:
  - 新建 6 个 Epic 文件 (epic-1 平铺, epic-2~6 展开)
  - 新建 25 个 Story 文件
  - kanban_board.md: Next Epic 11 → 17, Next Story 1 → 26

输入 confirm 写盘 / 输入 adjust 修订 / 输入 abandon 放弃
输入 expand epic-N 展开第 N 个 Epic 的完整 AC 详情
```

## §E Phase 4 — 模糊 AC 改写示例

```markdown
# ❌ 模糊（不可测试）
- [ ] 系统发送 6 位数字验证码短信

# ✅ 可测试
- [ ] 调用发送验证码 API 后，verification_codes 表新增一条记录，
      code 为 6 位数字，expired_at = now + 5min
      `验证: API POST /auth/send-code → 200; DB SELECT FROM verification_codes → code LIKE '[0-9]{6}'`

# ❌ 模糊
- [ ] 注册页面包含 App Logo 和标题

# ✅ 可测试
- [ ] 注册页面顶部显示 App Logo（img[alt="logo"]），下方 h1 文案为"食光记"
      `验证: Browser 访问 /register → img[alt="logo"] 存在 + h1.textContent === "食光记"`
```
