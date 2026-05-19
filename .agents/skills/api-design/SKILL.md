---
name: api-design
description: 在 Story 或实现过程中接口契约发生变化时，按需生成或更新 API 契约增量说明。适用于新增端点、请求/响应 schema、鉴权、错误码、分页与过滤规则变化；默认不生成完整 API 文档，除非用户明确要求。
---

# api-design

用于“接口契约发生变化，需要补 API 设计说明”的场景。

默认定位：
- 这是一个 **按需增量更新** workflow
- 不是每个 Story 都要跑
- 不是 `do-story` 的默认前置步骤

只有在以下情况命中时才使用：
- 新增或删除对外 API 端点
- 请求体、响应体、错误码、分页或过滤规则发生变化
- 鉴权、权限、幂等、回调、流式响应等契约变化需要明确说明
- 前后端联调前，需要把接口约束写清楚

通常不需要使用本 skill 的情况：
- 纯内部重构，不改 API contract
- 只改 service/repository/domain 细节
- 只是修复实现 bug，但接口不变

## 输入优先级

按以下顺序收集上下文：
1. 当前 Story / Plan / 验收标准
2. 现有架构文档：`docs/architecture.md`
3. 已存在的 API 设计文档：`docs/api-design.md` 或 Epic `source_documents.api_design`
4. 当前代码中的 route / DTO / test / 前端调用

如果现有 `docs/api-design.md` 不存在，不要默认要求创建完整文档。
先判断这次改动是否真的需要一个契约增量说明。

## Workflow

### Phase 0: 判断是否需要 API 设计更新

先回答这 4 个问题：
- 这次改动是否新增/修改了端点、方法、路径或版本？
- 这次改动是否改变了请求/响应 schema、错误码、分页/过滤、鉴权方式？
- 前端、第三方或其他服务是否依赖这次契约变化？
- 如果不写下来，后续联调或 review 是否容易产生歧义？

如果上述答案全部是否定：
- 明确说明“本次无需更新 API 契约文档”
- 停止，不生成文档

### Phase 1: 提取 API delta

如果需要更新，只输出本次变化相关的增量内容：
- 新增/修改/删除的端点
- 请求参数和请求体变化
- 响应体变化
- 错误码/业务错误变化
- 鉴权、幂等、分页、过滤、排序规则变化

推荐输出格式：

```md
## API Contract Delta

### Change Summary
- Added: `POST /api/v1/...`
- Updated: `GET /api/v1/...`
- Removed: `DELETE /api/v1/...`

### Endpoint Changes
| Change | Endpoint | Request | Response | Notes |
|--------|----------|---------|----------|-------|

### Error / Auth / Pagination Changes
| Topic | Before | After | Impact |
|-------|--------|-------|--------|
```

### Phase 2: 对齐实现与测试

把 delta 映射回代码实现：
- 哪些 route / DTO / serializer / response model 需要改
- 哪些前端调用或 API 测试需要同步改
- 哪些验收标准受影响

至少输出：
- 受影响文件清单
- 需要新增或更新的 API 测试
- 兼容性风险

### Phase 3: 写回文档

写回规则：
- 如果 `docs/api-design.md` 已存在：优先做增量更新，不重写整份文档
- 如果不存在，但本次变更确实需要沉淀契约：创建一个简洁版本，只包含当前相关模块
- 除非用户明确要求，不生成“大而全”的平台 API 文档

## 输出要求

默认输出应简短、面向当前 Story：
- 是否需要更新 API 契约
- 本次 API delta 是什么
- 影响哪些实现和测试
- 是否需要写回 `docs/api-design.md`

只有用户明确要求“完整 API 设计文档”时，才扩展为完整章节。

## 后置步骤：Codex 审查

**仅当 Phase 0 判定需要更新且文档实际生成/写回后**，自动执行 `codex-review`：
1. 调用 `codex-review` skill，传入刚生成或更新的 API 设计文档
2. Claude Code 自主判断 Codex 建议的采纳，修改文档后输出摘要
3. 用户可说"跳过审查"跳过此步骤

如果 Phase 0 判定"本次无需更新 API 契约文档"并停止，则不触发审查。

## 与其他 skill 的关系

- `codex-review`：文档生成后自动触发，做独立审查闭环
- `do-story`：主实现 workflow。它不会自动强制运行本 skill；只有命中 API 契约变化时才应调用本 skill。
- `story-reference-impl`：复杂 Story 研究/适配 workflow。只有当参考实现引入新的接口契约时，才补 API delta。
- `story-verify-fix`：验证实现是否符合验收标准，不替代 API 契约设计。
- `review`：审查契约实现是否一致，但不负责先生成契约。
