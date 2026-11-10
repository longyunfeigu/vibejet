# API-first 例外清单

记录测试数据实体的 REST API 可用性。有 API 的走 `core/api/entities/<x>.api.ts`;
无 API 的走 `core/api/entities/<x>.ui-fallback.ts`(仅语义定位),并在此说明原因。

| 实体 | create API | delete API | 状态 | 说明 |
|---|---|---|---|---|
| user(测试账号) | POST /api/v1/auth/register | ❌ 不提供 | ✅ 特例 | 只用 `Release-Check/_shared/fixtures.md` 的常驻账号;不存在时由 `config/global-setup.ts` 注册;绝不改密码和资料 |
| conversation | POST /api/v1/conversations | DELETE /api/v1/conversations/{conversation_id} | 🔍 未封装 | 第一个需要它的场景到来时封装为 `entities/conversation.api.ts`,并在 e2e-cleanup 登记清理 |
| agent-config | POST /api/v1/agent-configs | (待确认) | 🔍 未封装 | 同上 |
| document / file | (待确认) | (待确认) | 🔍 调研中 | 同上 |

> 状态:✅可用 / ⚠️UI-fallback / ❌无 / 🔍未封装或调研中。
