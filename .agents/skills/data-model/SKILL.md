---
name: data-model
description: 在 Story 或实现过程中持久化模型发生变化时，按需生成或更新数据模型增量说明。适用于新增实体、表结构、迁移、索引、约束和一致性策略变化；默认不生成完整数据模型文档，除非用户明确要求。
---

# data-model

用于“数据模型或持久化契约发生变化，需要补模型说明”的场景。

默认定位：
- 这是一个 **按需增量更新** workflow
- 不是每个 Story 都要跑
- 不是 `do-story` 的默认前置步骤

只有在以下情况命中时才使用：
- 新增实体、聚合、表、集合或重要值对象
- 新增 migration，或修改字段、索引、唯一约束、外键、软删除、审计字段
- 持久化层的一致性策略发生变化，例如 outbox、幂等键、状态机、乐观锁
- 需要把数据库 / ORM / 领域模型的映射关系明确写下来

通常不需要使用本 skill 的情况：
- 纯应用层或接口层调整，不改 schema / persistence contract
- repository 内部重构，但表结构和事务边界不变
- 只是修复实现 bug，但不影响模型或 migration

## 输入优先级

按以下顺序收集上下文：
1. 当前 Story / Plan / 验收标准
2. 现有架构文档：`docs/project/architecture.md`
3. 已存在的数据模型文档：`docs/project/database_schema.md` 或 Epic `source_documents.data_model`
4. 当前代码中的 domain entity、ORM model、migration、repository、测试

如果现有 `docs/project/database_schema.md` 不存在，不要默认要求创建完整文档。
先判断这次改动是否真的需要一个模型增量说明。

## Workflow

### Phase 0: 判断是否需要数据模型更新

先回答这 4 个问题：
- 这次改动是否新增/修改了表、字段、索引、约束或 migration？
- 这次改动是否改变了聚合边界、持久化映射或事务一致性策略？
- 这次改动是否会影响已有数据、迁移顺序或回滚方式？
- 如果不写下来，后续实现、review 或运维是否容易误解？

如果上述答案全部是否定：
- 明确说明“本次无需更新数据模型文档”
- 停止，不生成文档

### Phase 1: 提取数据模型 delta

如果需要更新，只输出本次变化相关的增量内容：
- 新增/修改/删除的实体或表
- 字段、类型、默认值、nullable、约束变化
- 索引与查询路径变化
- 事务边界、一致性、幂等或状态流转相关变化

推荐输出格式：

```md
## Data Model Delta

### Change Summary
- Added table: `...`
- Updated column: `...`
- Added index: `...`
- Migration required: yes/no

### Schema Changes
| Change | Object | Before | After | Notes |
|--------|--------|--------|-------|-------|

### Consistency / Transaction Notes
| Topic | Decision | Impact |
|-------|----------|--------|
```

### Phase 2: 对齐实现与迁移

把 delta 映射回代码实现：
- 哪些 domain entity / value object / repository interface 受影响
- 哪些 ORM model / migration / seed / fixture 需要改
- 哪些测试和回滚说明需要补

至少输出：
- 受影响文件清单
- 迁移风险与兼容性风险
- 需要新增或更新的 migration / integration test

### Phase 3: 写回文档

写回规则：
- 如果 `docs/project/database_schema.md` 已存在：优先做增量更新，不重写整份文档
- 如果不存在，但本次变更确实需要沉淀模型说明：创建一个简洁版本，只包含当前相关模块
- 除非用户明确要求，不生成“大而全”的全库 ER 文档

## 输出要求

默认输出应简短、面向当前 Story：
- 是否需要更新数据模型文档
- 本次 model delta 是什么
- 影响哪些实现、migration 和测试
- 是否需要写回 `docs/project/database_schema.md`

只有用户明确要求“完整数据模型设计文档”时，才扩展为完整章节。

## 后置步骤：Codex 审查

**仅当 Phase 0 判定需要更新且文档实际生成/写回后**，自动执行 `codex-review`：
1. 调用 `codex-review` skill，传入刚生成或更新的数据模型文档
2. Claude Code 自主判断 Codex 建议的采纳，修改文档后输出摘要
3. 用户可说"跳过审查"跳过此步骤

如果 Phase 0 判定"本次无需更新数据模型文档"并停止，则不触发审查。

## 与其他 skill 的关系

- `codex-review`：文档生成后自动触发，做独立审查闭环
- `do-story`：主实现 workflow。它不会自动强制运行本 skill；只有命中持久化模型变化时才应调用本 skill。
- `story-reference-impl`：复杂 Story 适配时，如果引入新的模型或一致性策略，再补 model delta。
- `story-verify-fix`：验证行为是否通过，不替代模型设计说明。
- `review`：审查 migration、事务和分层问题，但不负责先生成模型文档。
