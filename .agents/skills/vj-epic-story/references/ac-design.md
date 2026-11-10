# Story AC 设计与验证合同

`vj-epic-story` Phase 4 使用本参考。输出格式仍以 `epic-story.template.md` 为准，确定性结构
由 `scripts/validate_story.py` 拦截。

## 1. 分类

| 类别 | 用途 |
|------|------|
| Happy Path | 核心成功路径；必须至少 1 条 |
| Edge Cases | 空值、边界、重复、并发、非常规但合法输入 |
| Error Paths | 非法输入、超时、权限拒绝、下游/约束失败 |
| Integration | 跨层、跨模块、middleware、事件或副作用；跨层 Story 必填 |

分类提示只用于复核，不用于从通用清单凑 AC。

## 2. 先派生，再分类

| Story 形态 | 测试设计技术 | 候选 |
|------------|--------------|------|
| 输入字段 | 等价类划分 EP | 每个无效类 → Error AC；有实现风险差异的有效类（格式/编码/平台，如 HEIC 的 MIME 检测）→ 验证中逐类断言 |
| 数值/长度/日期/区间 | BVA：min-1/min/max/max+1 | 边界 → Edge AC；合法边界（min/max）是成功用例，不得只测越界 |
| 多条件决定结果 | 决策表；组合爆炸时 pairwise | 每条规则 → AC，并记录未覆盖组合 |
| 有状态实体/流程 | 状态 × 事件迁移表 | 合法迁移 + 至少一个非法迁移 |
| Story 内用户流程 | 主/备选/异常流走查 | 备选 → Edge，异常 → Error |

派生候选超过行为 AC 上限 7 时回 Phase 3 拆 Story，不删类别。低影响候选若明确裁剪，写入
`Assumptions [SCOPE]` 并说明失效影响。

## 3. AC 与验证格式

每条 AC 必须有明确结果、可执行验证、无“合理/正常/正确显示”等模糊词：

```text
验证: <kind> <target> → <assert>
```

`kind` 只能是 `pytest`、`API`、`DB`、`Browser`。target 必须是具体测试、路径、查询或 DOM
操作；assert 必须是状态码、字段、行数、元素状态或阈值。

| kind | target 示例 | assert 示例 |
|------|-------------|-------------|
| pytest | `test_code_expires_after_5min` | `PASSED` |
| API | `POST /auth/register` | `201 + body.token exists` |
| DB | `SELECT FROM users WHERE phone=X` | `1 row, is_active=true` |
| Browser | `click button[type=submit]` | `.toast visible, text=保存成功` |

`验证: Browser 打开页面`、`验证: API 调用接口`、`验证: pytest 跑测试` 均不合格。

验证必须覆盖 AC 文本承诺的每个可观察结果：文本写「可再次访问」，验证就必须含再次访问
的断言；一条验证盖不住就补断言或拆 AC。

## 4. 覆盖闸

每个 Story 输出前检查：

- 已按 Story 形态派生，而非通用清单凑数；每个派生候选可追溯——对应到具体 AC/断言，
  或写入 `Assumptions [SCOPE]` 裁剪。
- Happy 至少 1；适用的 Edge、Error、Integration 已覆盖。
- UI Story 有前端 AC；纯后端可标 N/A。
- 行为 AC ≤7；前端 AC 建议 ≤4，不能偷渡新业务行为。
- `#### Assumptions` 存在，无假设填“无”。
- 覆盖声明写派生（含候选→AC 映射，不接受裸 ✓）/Happy/Edge/Error/Integration/FE/数量/
  Assumptions 结果及 N/A 理由。

## 5. Assumptions

格式：

```text
[FEASIBILITY|DEPENDENCY|DATA|SCOPE] 描述 — Confidence: H|M|L — 失效影响: 可观察影响
```

不要写“会有问题”。没有假设时写：

```markdown
#### Assumptions
- 无
```

## 6. 前端来源

前端 AC 同时消费页面体验地图、`docs/project/DESIGN.md`、匹配设计稿和按缺口触发的 UI
skills。屏型最低 Browser 验证要求按 `_shared/ui-planning-contract.md` §4/§7。设计稿存在时
提取结构、交互和状态并把路径追加到 Story `参考`；不存在时从页面地图生成，不凭空造视觉。

模糊 AC 改写示例见 `references/display-formats.md` §E。
