# Feature Plan: [标题]

<!-- ═══ §0 Triage（必须） ═══ -->

## 0. Triage

### 需求摘要
- 本次要实现：

### 影响判定
- 用户目标数：1 / 多个
- 涉及模块：
- 涉及层级：[api / application / domain / infrastructure / frontend]
- 是否改 API 契约：是/否
- 是否改 DB schema：是/否
- 是否改 Domain 规则：是/否
- 是否涉及外部系统/异步：是/否
- 是否涉及权限/安全/幂等：是/否
- 预估文件数：

### 分级结论
- **Workflow**: Flow A / Flow B / Flow C
- **Confidence**: High / Medium / Low
- **理由**：

### 约束清单

从 Story AC、项目上下文和现有代码中提取约束，确保 plan 执行时零决策：

**硬约束**（AC 明确要求的）：
-

**隐含约束**（从现有代码/架构推导的）：
- 扫描现有代码，找出：已有的相关实现、已用的库/框架、已有的配置项、已有的接口模式
-

**需确认**（AC 没说，也推导不出，必须问用户的）：
-

> 规则：hardcoded 的数字、格式、策略选择如果 AC 没写，都列到"需确认"。不要默认选一个值然后实现到一半才发现不对。

### Scope Challenge
在进入设计前，先回答以下问题：
- 现有代码里已经有什么能复用，能避免平行实现？
- 达成目标的最小改动是什么？
- 哪些工作现在做属于 scope creep，可以延期？
- 如果预计修改超过 8 个文件或新增超过 2 个服务/抽象，是否说明方案过重？

### 本次必须产出
- [x] Plan
- [ ] 更新 api-design.md
- [ ] 更新 data-model.md
- [ ] 补 ADR

### 升级触发条件
- 如果发现 [xxx]，升级到 Flow [X]

<!-- ═══ 第 1 层：3 分钟看懂（Flow A/B/C 必填） ═══ -->

## 1. 目标
- 要解决的问题：
- 改完后的用户结果：

## 2. 范围

### In Scope
-

### Out of Scope
-

### NOT in scope
明确列出本次刻意不做的内容，避免实现和 review 时 scope 漂移：
- 不做：
- 延后到后续 Story / PR 的内容：

## 3. 影响范围

| 文件/模块 | 操作 | 说明 |
|-----------|------|------|
| `path/file.py` | 新建/修改 | ... |

**不会修改**：

## 4. 风险
- 主要风险：
- 边界情况：
- 回滚方式：

## 5. 验收标准
- [ ] ...

<!-- ═══ 第 2 层：10 分钟看懂（Flow B/C 填写） ═══ -->

## 6. 术语与代码对象
> 5+ 新概念时加此节
- `Xxx`：一句话解释

## 7. 当前现状
- 当前流程：
- 当前问题：

### What already exists
列出已存在且可复用的代码、流程、端口、模型、测试模式：
- 已有实现：
- 可直接复用：
- 需要改造复用：
- 不应重复建设的部分：

## 8. 方案概述
- 改动思路：
- 为什么这样做：

## 8.1 API Contract Delta
> 仅当 Triage 判定“是否改 API 契约 = 是”时填写；没有独立 `docs/api-design.md` 时，本节就是当前 Plan 的接口契约基线

### 受影响消费者
- Web / Frontend:
- Mobile:
- Internal Service / Worker:
- Third-party:

### 端点变化
| Change | Endpoint | Request | Response | Auth / Idempotency / Notes |
|--------|----------|---------|----------|-----------------------------|
| Added / Updated / Removed | `POST /api/v1/...` | body/query/path 变化 | 返回结构变化 | ... |

### 错误与兼容性变化
| Topic | Before | After | Impact |
|-------|--------|-------|--------|
| Error code / status / pagination / filter / sort / streaming | ... | ... | ... |

### 测试与联调影响
- 需要新增/修改的 API 测试：
- 需要同步修改的前端调用：
- 是否需要补 `docs/api-design.md` 增量说明：是/否

## 8.2 设计参考
> 仅当前端 Story 且有设计稿时填写；优先让 `do-story` 可自动发现

### 设计参考表
| 页面/状态 | 参考图路径或 URL | 类型 | 说明 |
|-----------|------------------|------|------|
| List / Empty / Loading / Success / Error | `docs/designs/{epic-id}/{story-id}-{page}.png` | image / figma / url | ... |

### 说明
- 优先使用相对仓库根目录的路径
- 如同一页面有多个状态，请逐行列出
- 如不填写，默认按 `docs/designs/{epic-id}/` 下以 `{story-id}` 开头的文件自动发现

## 9. 核心流程
> 涉及状态流转/异步/外部调用/权限/多步骤时加此节

### 改动前
```mermaid
flowchart TD
```

### 改动后
```mermaid
flowchart TD
```

### Failure Modes & Test Diagram
对每条关键新路径，明确失败方式、可见性和测试覆盖：

| Codepath / Interaction | Failure mode | 系统行为 | 用户可见性 | 测试类型 |
|------------------------|--------------|----------|------------|----------|
| `service.call()` | timeout / invalid state / race / stale data | ... | ... | unit / integration / api / e2e |

可以用 ASCII 图补充：

```text
请求进入
  -> 参数校验
  -> 业务编排
  -> 持久化 / 外部调用
  -> 响应

失败路径:
  - 参数非法 -> 422 / BusinessException
  - 并发冲突 -> 409 / retry / 幂等处理
  - 外部系统失败 -> 降级 / 重试 / 明确错误
```

<!-- ═══ 第 3 层：需要时再看（Flow C 填写） ═══ -->

## 10. 关键实现细节
> 涉及 DB 迁移/缓存/幂等/事务/并发等高风险点时加此节
- 数据结构变化：
- 状态流转规则：
- 异常处理：
- 兼容性处理：

## 10.1 Schema / Migration Delta
> 仅当 Triage 判定“是否改 DB schema = 是”时填写；没有独立 `docs/data-model.md` 时，本节就是当前 Plan 的模型变化基线

### 对象变化
| Change | Table / Object | Before | After | Notes |
|--------|----------------|--------|-------|-------|
| Added / Updated / Removed | `orders.cancel_reason` | ... | ... | ... |

### 索引 / 约束 / 一致性
| Topic | Before | After | Impact |
|-------|--------|-------|--------|
| Index / unique / FK / transaction / outbox / idempotency | ... | ... | ... |

### Migration 与验证
- 需要的 migration：
- 数据兼容性 / 回填策略：
- 回滚方式：
- 需要新增/修改的 integration test：
- 是否需要补 `docs/data-model.md` 增量说明：是/否

<!-- ═══ 执行（所有 Flow） ═══ -->

## 11. 执行步骤
> Flow A: 可合并为 1-2 步
> Flow B/C: 分步，每步 = 一个 task，完成后 commit

1. [ ] Step 1: [描述] -> 涉及文件: [...] -> commit
2. [ ] Step 2: [描述] -> 涉及文件: [...] -> commit
3. [ ] Step 3: [描述] -> 涉及文件: [...] -> commit + 全量测试
4. [ ] 完成后使用 story-verify-fix 验证
