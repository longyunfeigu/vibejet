---
name: review
description: 对当前分支、工作区或指定文件做 pre-landing code review。优先发现 DDD 分层违规、权限边界缺失、并发/事务风险、trust boundary 问题和缺失测试。默认基于 diff 做两轮审查，并使用 docs/reference/guides/review-checklist-python-fastapi.md 输出 findings-first 结果。
---

# review

用于本仓库的 pre-landing code review。

这个 skill 的目标不是润色代码风格，也不是重复 lint。它优先找那些测试可能没覆盖、但会在生产环境出问题的结构性缺陷。

## 适用场景

- 用户明确说“review”或“代码审查”
- 用户想在合并前检查当前分支改动
- 用户想审某个 PR、diff、文件集合或工作区改动
- 用户想确认复杂 Story 的实现是否存在回归风险

## 不适用场景

- 用户已经明确要求直接修改代码，而不是先 review
- 用户只是要解释代码或总结 diff，没有审查意图
- 用户只想跑测试，不需要结构化审查结论

## 默认范围

如果用户没有明确指定范围，按以下顺序确定 review 范围：

1. 当前分支相对 `origin/main` 的 diff
2. 如果没有 `origin/main`，则使用本地 `main`
3. 如果仍然不可用，则 review 当前工作区的未提交改动

如果用户指定了文件、目录、提交范围或 PR 范围，则以用户指定范围为准。

## 必读基线

开始 review 前必须读取：

- `docs/reference/guides/review-checklist-python-fastapi.md`

如果该文档缺失或无法读取，应停止并直接报告，不要假装按标准审查。

## Workflow

### Step 1: Determine Scope

1. 确认当前 review 的目标范围。
2. 如果是分支 review，优先找出相对 `main` 的完整 diff，而不是只看最近几个文件。
3. 如果没有任何差异，直接输出：

```text
Review: No changes to review.
```

### Step 2: Read Full Context Before Judging

1. 先读完整 diff，再看具体文件内容。
2. 必要时补读被修改文件的上下文、相关接口、相关测试。
3. 不要在只看局部片段时提前下结论。
4. 如果问题已经在同一 diff 中被修掉，不要重复报。

### Step 3: Two-Pass Review

严格按两轮执行，避免风格问题淹没真正风险。

#### Pass 1: Blocking

优先检查这些问题：

- DDD 分层违规
- 权限与数据边界缺失
- 并发、幂等、状态流转风险
- 事务与 side effect 不一致
- 外部输入 / SDK / LLM trust boundary
- 不安全持久化与查询
- 默认安全配置过宽

**安全加检**（当改动涉及认证、授权、用户输入、外部集成时）：
- 读取 `references/security-checklist.md`，重点检查 A.2-A.5 节
- Secrets 硬编码、CORS `allow_origins=["*"]`、未校验输入直接入库 → 均为 blocking

这类问题默认视为 blocking，除非有清晰证据证明风险不存在。

#### Pass 2: Non-blocking

再检查这些问题：

- API 契约与响应一致性
- 异常模型一致性
- 日志与可观测性
- DTO / Entity / ORM 职责混淆
- 测试缺口
- 性能与资源使用
- 魔法值与重复实现

**性能加检**（当改动涉及数据库操作、列表查询、外部调用、文件处理时）：
- 读取 `references/performance-checklist.md`，重点检查 B.1-B.3 节
- N+1 查询、无分页的全表查询、同步阻塞计算在请求处理器中 → 建议标为 blocking 或 high-priority non-blocking

### Step 4: Output Findings First

输出顺序必须是：

1. `Blocking`
2. `Non-blocking`
3. `Open questions / assumptions`
4. 可选的简短 change summary

不要先写概述，再把问题放到后面。

建议格式：

```md
Review: N issues (X blocking, Y non-blocking)

Blocking:
- [abs/path/file.py:123] 问题
  Fix: 修复建议

Non-blocking:
- [abs/path/file.py:45] 问题
  Fix: 修复建议

Open questions / assumptions:
- ...
```

要求：

- 问题按严重级别排序
- 每条尽量给出文件和行号
- 优先指出 bug、回归风险和缺失测试
- 避免无意义风格建议

### Step 5: No-Issue Case

如果没有发现问题，也要明确输出：

```text
Review: No issues found.
```

然后补一句 residual risk 或 testing gap，例如：

- 未运行测试
- 仅审查了指定文件，未覆盖相邻调用方
- 某些高风险路径因上下文不足未完全验证

## Review Rules

1. 默认只读。除非用户明确要求修复，否则不要顺手改代码。
2. 只报真实问题。不要为了“显得认真”强行找问题。
3. 先看完整 diff，再评价局部实现。
4. 重点关注行为风险，不关注个人风格偏好。
5. 如果测试缺口本身会掩盖风险，要把缺失测试当成问题报出来。
6. 如果用户要求 review 某个 Story，实现与验收标准冲突也要报。

## 与其他 skills 的关系

- `vj-work`
  - Story/Unit 实现完成后，可用本 skill 做 pre-landing review（strict 模式默认触发）
- `story-reference-impl`
  - 复杂 Story 在 verify-fix 通过后，再用本 skill 做结构化审查
- `story-verify-fix`
  - 先验证功能和联调，再用本 skill 找结构性风险和缺失测试

推荐顺序：

1. 实现
2. verify-fix
3. review

## Common Rationalizations

| 偷懒借口 | 现实 |
|---------|------|
| "代码能跑，测试也过了，应该没问题" | 测试通过是必要条件不是充分条件。测试不会告诉你 DDD 分层违规、权限边界缺失、或并发风险。 |
| "这个改动太小了，不值得做 review" | 小改动也能引入安全漏洞或破坏架构约束。2 行代码加一个错误的 import 就能打穿 Domain 层隔离。 |
| "AI 生成的代码看着很合理" | AI 代码需要更多审查而不是更少。它写出来的东西自信且合理，即使是错的。 |
| "我只看了改动的文件就够了" | 改动的文件只是冰山一角。不看调用方、不看接口定义、不看相关测试，你会漏掉回归风险。 |
| "这是内部 API，不需要校验输入" | 内部 API 今天内部，明天可能暴露。Trust boundary 不看调用者是谁，看数据从哪来。 |
| "Pass 1 没发现 blocking 问题，Pass 2 可以简单过一下" | Pass 2 的 non-blocking 问题积累起来就是技术债。测试缺口、日志缺失、DTO 混用不会立即爆炸，但会在生产环境慢慢腐蚀。 |
| "风格问题不重要，跳过" | 这个 skill 本来就不管风格。但如果你把"异常模型不一致"或"DTO 职责混淆"当成风格问题跳过，那是在回避真正的结构性问题。 |

## Red Flags

出现以下任何一条，说明 review 质量不达标：

- 没有先读完整 diff 就开始逐文件评价
- 只做了 Pass 1 就跳过 Pass 2
- 输出里先写了一大段"总体不错"的概述，问题藏在最后
- `docs/reference/guides/review-checklist-python-fastapi.md` 没有被读取就开始审查
- Blocking 问题被标成了 Non-blocking（降级逃避）
- 发现 DDD 分层违规但没有标记为 blocking
- 审查涉及数据库操作但没有检查事务边界
- 审查涉及外部输入但没有检查 trust boundary
- 改动涉及认证/授权但没有对照附录 A 检查
- 改动涉及数据库查询但没有检查 N+1 和分页
- diff 中出现 `allow_origins=["*"]` 或硬编码 secret 但未报 blocking
- 输出"No issues found"但没有附 residual risk 说明

## 示例

审查当前分支：

```text
使用 review，审查当前分支相对 main 的改动。
```

审查指定文件：

```text
使用 review，重点审查 api/routes/files.py 和 application/services/file_asset_service.py。
```

审查某个 Story 的实现：

```text
使用 review，审查 story 3.5 的实现，优先找 blocking 问题和缺失测试。
```
