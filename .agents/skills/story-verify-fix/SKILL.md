---
name: story-verify-fix
description: 从 Story 文件或 Story 描述启动“环境启动 → Story 验证 → 前后端联调 → 设计图对齐检查 → 自动修复重试”的 workflow。适用于需要同时验证后端、前端、集成行为和 UI 对齐的复杂 Story。
---

# story-verify-fix

用于把一个 Story 的实现拉到“可验证、可修复、可收敛”的状态。

这个 skill 不是泛 QA，也不是全站探索测试。它只围绕当前 Story 的验收标准、关键用户流、前后端集成行为和可选的设计参考图来工作。

## 适用场景

- Story 同时涉及后端和前端，需要联调验证
- Story 需要 AI 在实现后自己跑验证，并在失败时继续修代码
- Story 有明确验收标准，需要做确定性验证
- Story 提供了页面设计参考图，需要验证 UI 是否与设计对齐
- 用户希望先验证当前 Story，再决定是否进入 review

## 不适用场景

- 用户只是要求做人工式 exploratory QA，没有明确 Story 边界
- 仓库没有可启动的服务入口，且无法从本地上下文或用户输入中确定
- Story 验收标准、页面入口或设计参考信息严重缺失
- 需要做大规模全站回归，而不是单个 Story 的验证闭环

## 输入要求

优先从 Story 文件、现有设计文档和仓库脚本中自动提取；不足时再向用户补最少信息。

至少识别以下信息：

- Story 路径或 Story 内容
- Story 验收标准
- 是否涉及后端
- 是否涉及前端
- 后端启动命令或可推断入口
- 前端启动命令或可推断入口
- 后端 Base URL
- 前端 Base URL
- 是否存在设计参考图
- 关键页面 / 关键用户流
- 最大自动修复轮次

默认值：

- `max_fix_loops = 3`
- 优先只重跑受影响的验证，不做整套全量重跑
- 视觉检查默认为结构与关键视觉点比对，不做像素级 diff

## 核心原则

1. 只验证当前 Story，不扩展成整站 QA。
2. 先做确定性验证，再做浏览器联调，再做视觉对齐。
3. 环境启动失败、依赖缺失、端口冲突这类环境问题，不应直接进入修代码循环。
4. 自动修复循环必须有上限；同类失败重复出现应停止并报告。
5. 视觉检查的目标是发现明显偏差，不追求第一版就做到像素级自动判定。
6. 修复时优先最小改动，不随意扩大 Story 范围。

## Browser Verification Contract

当 Story 涉及前端页面、用户操作链路或视觉对齐时，默认浏览器执行器为：

- `web-access`（Chrome CDP 模式）

使用要求：

1. 使用前先运行 `bash ~/.claude/skills/web-access/scripts/check-deps.sh` 确保 CDP Proxy 就绪。
2. Phase 3 和 Phase 4 优先复用同一个 CDP tab（通过 targetId），避免每一步都重新创建 tab。
3. 浏览器验证必须围绕 Story 的关键用户流执行，不做无关页面漫游。
4. 每次前端联调至少收集以下证据：
   - 当前页面截图（`/screenshot?target=ID&file=path`）
   - 关键失败步骤
   - 控制台错误（通过 `/eval` 捕获 `window.__errors` 或监听 console）
   - 失败请求或异常响应（通过 `/eval` 检查网络状态）
5. 如果 Story 提供设计参考图，则视觉检查默认比较”关键状态页面”的截图，而不是任意页面。
6. 修复后优先重跑受影响的浏览器链路与对应视觉检查，不做全量前端回归。
7. 验证完成后用 `/close` 关闭自己创建的 tab，不影响用户已有的 Chrome tab。

关键状态页面通常包括：

- 首次进入页面后的默认态
- 提交成功态
- 关键错误态
- 设计图明确给出的空态 / 加载态 / 结果态

## Workflow

### Phase 0: Intake & Verification Plan

1. 读取 Story 文件或用户给出的 Story 描述。
2. 提取验收标准、关键用户流、前后端边界和设计参考信息。
3. 判断当前 Story 的验证模式：
   - `backend-only`
   - `full-stack`
   - `full-stack + visual`
4. 确认后端启动入口、前端启动入口、健康检查接口、关键页面入口。
5. 输出一个简短验证计划，至少包含：
   - 当前模式
   - 需要启动哪些服务
   - 将执行哪些验证
   - 是否会做视觉对齐
   - 自动修复上限

当以下信息缺失时，先停在 Phase 0：

- 后端或前端无法确定如何启动
- Story 验收标准过于模糊，无法转成验证动作
- 设计参考图被要求检查，但路径缺失或不可读取

### Phase 1: Environment Bring-Up

1. 启动后端服务，并验证 readiness。
2. 如果 Story 涉及前端，则启动前端服务，并验证页面可访问。
3. 验证前端是否指向当前后端，而不是错误环境。
4. 记录启动命令、端口、健康检查结果和失败日志。

最低要求：

- 后端至少通过一个健康检查，例如 `/health/live`、`/health` 或等价端点
- 前端至少能打开目标页面或应用入口

如果 Phase 1 失败：

- 先尝试修正明显的本地环境问题或启动参数问题
- 如果仍然无法稳定启动，则停止，不进入修代码循环

### Phase 2: Deterministic Story Verification (逐条 AC 验证)

**核心变化**：不再笼统跑测试，而是**逐条 AC 出具验证证据**。

#### Step 1: 提取 AC 清单

从 Story 文件中提取所有 AC checkbox，构建验证清单：

```markdown
| # | AC 原文 | 验证方式 | 状态 |
|---|---------|---------|------|
| 1 | (从 Story 逐条复制) | (从 AC 的 `验证:` 标注提取) | pending |
| 2 | ... | ... | pending |
```

如果 AC 没有 `验证:` 标注：
- **新 Story**（由 epic-story-generator 生成）：视为 **blocking 问题**，停止验证并要求补充 `验证:` 标注
- **存量 Story**（无 `验证:` 标注的历史 AC）：根据 AC 内容推断验证方式，但在报告中标记为 `⚠️ 推断` 并建议回填

#### Step 2: 逐条执行验证

对每条 AC，按其验证方式执行：

| 验证方式 | 执行动作 |
|---------|---------|
| `pytest` | 运行指定测试：`cd backend && pytest tests/path/test_file.py::test_func -v` |
| `API` | 执行 curl/httpie 调用，断言状态码和响应体 |
| `DB` | 执行 SQL 查询，断言行数和字段值 |
| `Browser` | 通过 web-access CDP 执行操作，断言 DOM 状态 |

**数据库状态校验（写入类 AC 必须执行）**：

当 AC 涉及数据写入（注册、创建、更新等），在 API 调用成功后必须直接查询数据库验证数据已落库：

```bash
sqlite3 backend/dev.db "SELECT id, phone, is_active FROM users WHERE phone='13800001234';"
```

如果 DB 查询结果为空但 API 返回了 200，说明事务未提交或连接隔离问题，必须作为 **blocking issue** 报告。

#### Step 3: 输出 AC 验证报告

**输出格式（BLOCKING — 有 ❌ 则 Story 不算完成）**：

```markdown
## AC 验证报告

| # | AC | 验证方式 | 证据 | 结果 |
|---|-----|---------|------|------|
| 1 | 验证码 5 分钟过期 | pytest test_code_expires | PASSED (0.3s) | ✅ |
| 2 | 60 秒内不可重发 | API POST /auth/send-code × 2 | 第二次返回 429 | ✅ |
| 3 | 注册后 users 表有记录 | DB SELECT FROM users | 1 row, phone=138xxx | ✅ |
| 4 | 每日上限 10 条 | pytest test_daily_limit | FAILED: 无此测试 | ❌ |

**通过率: 3/4 (75%)**

### ❌ 未通过的 AC
- #4: 每日上限 10 条 — 原因: 测试缺失，需补充 test_daily_limit
```

**证据要求**：
- `pytest`: 测试名 + PASSED/FAILED + 耗时
- `API`: 请求 + 响应状态码 + 关键响应字段
- `DB`: 查询语句 + 返回行数 + 关键字段值
- `Browser`: 操作步骤 + DOM 断言结果 + 截图路径（如适用）

**判定规则**：
- 所有 AC ✅ → Story 验证通过，进入 Phase 3（如涉及前端）或 Phase 6
- 任一 AC ❌ → 进入 Phase 5 Fix Loop，修复后重跑失败的 AC（不全量重跑）

### Phase 3: Full-Stack Integration Verification

如果 Story 涉及前端，则执行浏览器驱动的联调验证。

重点验证：

- 页面是否能完成 Story 关键用户流
- 前端请求是否成功命中后端
- UI 状态是否与后端状态一致
- loading / empty / error / success 等关键状态是否可用

这一阶段不是泛探索，而是围绕 Story 的关键操作链路，例如：

- 打开页面
- 输入表单
- 点击按钮
- 等待请求返回
- 校验页面结果与后端结果一致

执行要求：

- 默认使用 `web-access`（Chrome CDP 模式），通过 `/new`、`/eval`、`/click`、`/screenshot` 等 API 操作页面
- 尽量复用同一个 CDP tab（targetId）完成关键链路
- 记录关键操作步骤与对应页面状态
- 对失败步骤保留截图、控制台错误和失败请求证据

### Phase 4: Visual Alignment Verification

只有在 Story 或相关文档提供设计参考图时才执行。

检查目标：

- 页面整体结构是否匹配设计意图
- 关键布局、主要组件层级、按钮位置、间距关系是否明显偏离
- 关键状态页是否缺失设计中已有的元素

第一版只做轻量视觉对齐检查：

- 页面截图
- 与设计参考图做结构和关键视觉点比对
- 标记“通过 / 明显偏差 / 需人工确认”

不要在第一版默认做像素级截图 diff。

优先比较的页面状态：

- Story 关键成功态
- 设计图明确给出的状态页
- 最容易出现布局偏差的主页面或主容器

### Phase 5: Fix Loop

当 Phase 2、3、4 任一失败时，进入有限自动修复循环。

循环规则：

1. 先分类失败：
   - 环境问题
   - API / 后端行为错误
   - 前后端联调错误
   - UI 交互错误
   - UI 视觉偏差
   - 测试脚本或验证脚本自身问题
2. 只对代码或验证脚本做最小必要修改。
3. 优先重跑受影响的验证，不做无关重跑。
4. 如果失败发生在 Phase 3 或 Phase 4，优先重跑对应的浏览器链路和相关截图检查。
5. 每轮修复后记录：
   - 改了什么
   - 为什么改
   - 重跑了什么
   - 是否有进展
6. 默认最多修复 3 轮。

必须停止并报告的情况：

- 同一类失败连续出现且没有实质进展
- 失败根因是需求冲突、设计图冲突或环境不可用
- 修复已经明显超出当前 Story 范围

### Phase 6: Final Report

最终输出必须是结构化结论，至少包括：

- Story 标识
- 验证模式
- 后端验证结果：`passed / failed / skipped`
- 前后端联调结果：`passed / failed / skipped`
- 视觉对齐结果：`passed / partial / failed / skipped`
- 自动修复轮次
- 剩余未解决问题
- 关键证据：
  - 失败接口或断言
  - 关键日志
  - 截图或页面证据

如果当前 Story 已通过验证，建议再进入仓库的 review 流程，并优先套用：

- `docs/reference/guides/review-checklist-python-fastapi.md`

## Stop Conditions

出现以下情况时，应停止继续自动修复，并向用户明确报告：

- 无法确定可靠的启动方式
- 前端源码或构建入口不可用，无法做联调
- Story 验收标准与设计参考图明显冲突
- 设计参考图缺失、损坏或无法读取
- 环境依赖缺失导致验证不可重复
- 同类错误在上限轮次内没有收敛

## Common Rationalizations

| 偷懒借口 | 现实 |
|---------|------|
| "后端测试过了，前端肯定没问题" | 后端测试验证的是 API 契约，不是页面行为。前端可能拿到正确数据但渲染错误、状态管理出 bug、或者根本没调对端点。 |
| "我手动打开页面看了一眼，没问题" | "看了一眼"不是验证。没有截图证据、没有 DOM 断言、没有走完关键用户流，这不算验证通过。 |
| "只是改了样式，不需要跑 AC 验证" | 样式改动可能破坏布局、隐藏元素、影响交互区域。逐条 AC 验证不贵，跳过它的代价是线上才发现 UI 坏了。 |
| "这条 AC 太难自动验证，跳过" | 难验证 ≠ 可以跳过。如果自动验证不了，在报告中标记为"需人工验证"并说明原因，而不是假装它不存在。 |
| "环境启动失败，先跳过环境直接验证" | 环境不稳定时的验证结果不可信。Phase 1 失败就应该停下来解决环境问题，而不是在不稳定的环境上继续。 |
| "修了 3 轮还没过，再多修几轮应该能收敛" | 3 轮没收敛说明问题根因没找对。继续盲修只会引入更多副作用。应该停下来报告，让人介入诊断。 |
| "视觉上差不多就行，不用对设计图" | "差不多"是主观判断。截图 + 设计图对比是客观证据。明显偏差不修复，上线后用户会发现。 |
| "这个 Story 只有后端，不需要浏览器验证" | 如果 Story 确实只有后端，Phase 3 会被正确跳过。但如果 Story 的 AC 里有任何"页面显示"或"用户看到"的描述，它就不是纯后端 Story。 |

## Red Flags

出现以下任何一条，说明验证不充分：

- AC 验证报告中只有 happy path 通过，没有验证错误流程和边界条件
- 跳过了 Phase 3（前端联调）但 Story 的 AC 包含前端行为描述
- 说"UI 正常"但没有截图证据
- 数据库有写入操作但没有执行 DB 查询验证数据落库
- Phase 5 Fix Loop 中同一类错误连续出现但没有停止
- 验证报告中有 ❌ 但最终结论写的是"验证通过"
- 设计参考图存在但 Phase 4 被跳过
- 浏览器验证只打开了页面但没有执行任何交互操作
- AC 验证方式全部是"推断"（⚠️），没有一条来自 Story 原始标注

## 使用建议

适合与以下 workflow 组合：

- `story-reference-impl`
  - 先做参考实现研究与适配设计，再实现，再用本 skill 验证收敛
- `do-story`
  - 先完成 Story 实现，再用本 skill 做 Story 级 verify-fix

推荐顺序：

1. 实现 Story
2. 使用 `story-verify-fix` 做验证和自动修复
3. 验证通过后，再进入 review

## 示例

后端 Story：

```text
使用 story-verify-fix，处理 docs/tasks/epics/epic-03-agent-execution.md#story-3.2，只启动后端并验证验收标准。
```

前后端联调 Story：

```text
使用 story-verify-fix，处理 docs/tasks/epics/epic-03-agent-execution.md#story-3.5。
后端启动命令是 uvicorn main:app --reload --port 8000
前端启动命令是 npm run dev -- --port 3000
需要做前后端联调验证。
```

带设计图对齐检查的 Story：

```text
使用 story-verify-fix，处理 docs/tasks/epics/epic-04-console.md#story-4.1。
启动前后端，并验证页面与 Story 中的设计参考图是否对齐。
最多自动修复 2 轮。
```
