# core/api — API-first 测试数据层

所有测试实体的建/删/查的**唯一入口**。steps/pages 禁止直接用 `page.request.*` 做数据 CRUD(由 `lint:bdd` Check H 守护)。

## 结构

```
core/api/
├── client.ts          ApiClient:封装 page.request、baseURL、超时、region 推导、错误日志
├── registry.ts        泛化多实体清理注册中心(per-worker、幂等、按类型登记 id)
├── entities/
│   └── agent.api.ts   agentApi:create / list / delete / deleteByName / ensureFresh
├── baseline-snapshot.json  agentApi.create 的导入模板(由 snapshot:capture:uat 捕获)
└── EXCEPTIONS.md      无 REST API 的实体清单 + UI fallback 说明
```

## 用法

```ts
import { AgentApi } from '../../../core/api/entities/agent.api';

const api = new AgentApi(page);
const id = await api.ensureFresh('e2e-hotwords-va030'); // 删同名再建,自动登记清理
// ... 被测步骤 ...
// 无需手动删:全局 After(modules/common/steps/e2e-cleanup.steps.ts)按 registry 兜底清理
```

## 错误处理两策略

- **清理**(`safeDelete` / After)= best-effort,永不抛,只 `console.warn`。
- **前置准备**(`create` / `getJson` / `post`)= 必须抛(fail-fast),带 HTTP 状态 + body。

## 相关脚本

- `npm run test:unit` — registry / client 纯逻辑单测
- `npm run snapshot:capture:uat <agentId>` — 捕获 baseline 快照
- `npm run test:api:uat` — agentApi create→get→delete 连通性冒烟
