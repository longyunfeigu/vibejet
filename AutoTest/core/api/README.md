# core/api — API-first 测试数据层

所有测试实体的建/删/查的**唯一入口**。steps/pages 禁止直接用 `page.request.*` 做数据 CRUD(由 `lint:bdd` Check H 守护)。

## 结构

```
core/api/
├── client.ts          ApiClient:封装 page.request、Bearer 鉴权(取页面登录态里的 access token)、超时、错误日志
├── registry.ts        泛化多实体清理注册中心(per-worker、幂等、按类型登记 id)
├── entities/          每种实体一个 <x>.api.ts(create / delete / ...),第一个需要它的场景到来时再建
└── EXCEPTIONS.md      各实体的 REST API 可用性清单
```

## 用法

```ts
import { ApiClient } from '../../../../core/api/client';

// 验证数据真相(读):当前登录账号
const me = await new ApiClient(page).getJson<{ data: { username: string } }>('/api/v1/auth/me');
```

实体工厂的约定(第一个实体到来时照此实现):`create()` 成功后 `registry.register('<type>', id)`;
在 `modules/common/steps/e2e-cleanup.steps.ts` 的 `CLEANUP` 里登记该类型的删除函数,全局 After 兜底清理。

## 错误处理两策略

- **清理**(`safeDelete` / After)= best-effort,永不抛,只 `console.warn`。
- **前置准备**(`create` / `getJson` / `post`)= 必须抛(fail-fast),带 HTTP 状态 + body。
