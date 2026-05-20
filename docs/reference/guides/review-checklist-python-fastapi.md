# Python / FastAPI Review Checklist

适用于本仓库的后端代码审查。目标不是泛泛检查“代码风格”，而是优先发现会在生产环境出问题的结构性缺陷。

适用范围：
- `api/`
- `application/`
- `domain/`
- `infrastructure/`
- `core/`
- 相关测试

---

## 1. 使用方式

审查时，先看完整 diff，再按两轮执行：

1. **Pass 1: Blocking**
   检查会导致分层破坏、安全问题、数据不一致、并发问题、权限泄漏、事务错误的项。
2. **Pass 2: Non-blocking**
   检查可维护性、可观测性、测试缺口、性能和一致性问题。

建议输出格式：

```md
Review: N issues (X blocking, Y non-blocking)

Blocking:
- [file:line] 问题
  Fix: 修复建议

Non-blocking:
- [file:line] 问题
  Fix: 修复建议
```

如果没有问题，明确写：`Review: No issues found.`

---

## 2. Pass 1: Blocking

这些问题默认视为阻塞合并或至少阻塞“已完成”判断。

### 2.1 DDD 分层违规

检查：
- `domain/` 是否导入了 `api` / `application` / `infrastructure`
- `application/` 是否直接依赖 ORM model、数据库细节或 FastAPI 对象
- `api/` 是否直接写业务逻辑或直接操作 repository / session
- `infrastructure/` 是否反向依赖 `api`

要抓的典型问题：
- route 里直接拼装 SQLAlchemy 查询
- application service 直接 import `infrastructure.models.*`
- domain entity 调外部 SDK 或 Redis

例子：

```python
# bad
from infrastructure.models.file_asset import FileAssetModel
```

Fix:
- 把 ORM 访问收回 repository / infrastructure
- application 只通过 port / repository 接口编排

### 2.2 权限与数据边界

检查：
- 是否存在 `No permission check`
- 是否把 `user_id=None`、匿名主体、默认 owner 直接写死在业务路径里
- 是否能通过 ID 枚举访问别人的资源
- 是否缺少 tenant / owner 过滤

要抓的典型问题：
- 详情接口按 `asset_id` 直接返回
- 删除接口不校验资源归属
- 列表接口默认返回全量数据

例子：

```python
asset = await service.get_asset_raw(asset_id)
# No permission check
```

Fix:
- 注入 `current_actor`
- 在 application 层显式校验 owner / role / tenant boundary
- API 测试补未授权和越权场景

### 2.3 并发、幂等与状态流转安全

检查：
- check-then-act 是否存在竞态
- 幂等键是否真正绑定请求哈希
- 状态流转是否允许重复执行 side effect
- 是否在非原子路径里读状态、改状态、再触发外部动作

要抓的典型问题：
- `if status == "pending": status = "done"` 没有原子约束
- 重试时重复创建资源
- 并发请求下重复发消息 / 重复扣费 / 重复写日志

例子：

```python
if session.status == "running":
    session.status = "stopped"
    await repo.update(session)
```

Fix:
- 使用原子更新或版本号 / 条件更新
- 补并发测试或重复请求测试
- 把 side effect 放到事务边界清晰的位置

### 2.4 事务与 side effect 一致性

检查：
- DB 写入与外部调用是否处于不一致窗口
- 是否先调用外部系统，再写本地状态，失败后无补偿
- UoW 是否在该 commit 时 commit，该 rollback 时 rollback
- “best effort” 是否会造成静默数据不一致

要抓的典型问题：
- DB 已成功，外部动作失败但无补偿
- 外部动作成功，DB rollback 后状态漂移
- 吞掉异常后继续返回成功

例子：

```python
try:
    await self._storage.delete(asset.key)
except Exception:
    pass
```

Fix:
- 明确这是可接受的幂等删除，还是需要补偿 / 标记失败
- 记录结构化日志和失败状态
- 必要时引入 outbox / retry / reconciliation

### 2.5 外部输入与 LLM / SDK Trust Boundary

检查：
- 外部系统、SDK、LLM、HTTP 请求、文件元数据是否在边界做了校验
- DTO 是否足够约束 shape / type / range
- 非法值是否会直接入库或进入 domain entity

要抓的典型问题：
- `dict` 直接喂给 entity
- email/url/path 未校验
- 文件名、header、content type 直接透传

Fix:
- 在 DTO 或 adapter 边界用 Pydantic 校验
- 抛 `BusinessException` / `DomainValidationException`
- 补负路径测试

### 2.6 不安全持久化与查询

检查：
- 原始 SQL / 拼接 SQL
- repository 过滤条件是否直接透传不受控字段
- 删除、更新是否缺少归属或状态限制
- 列表查询是否遗漏关键 where 条件

要抓的典型问题：
- query filters 没有限定 owner / status
- update/delete 只按主键，不按业务约束
- 查询在循环中执行导致隐性 N+1

### 2.7 安全配置与默认行为

检查：
- DEBUG 行为是否可能泄露 traceback / 内部信息
- 健康检查、metrics、管理接口是否需要 token 却未保护
- 上传、下载、预签名、文件访问的默认权限是否过宽

要抓的典型问题：
- 生产环境暴露过多细节
- 默认公开资源
- 临时签名过长、无约束

---

## 3. Pass 2: Non-blocking

这些问题通常不阻塞，但应记录和修复。

### 3.1 API 契约与响应一致性

检查：
- 是否统一使用 `core.response`
- HTTP status 与业务码是否匹配
- DTO 命名和字段语义是否稳定
- route summary / response_model 是否准确

### 3.2 异常模型一致性

检查：
- 业务错误是否统一使用 `BusinessException`
- domain validation 是否落在 `DomainValidationException`
- API 层是否滥用 `HTTPException`
- message_key / locale / field / details 是否按现有规则传递

### 3.3 日志与可观测性

检查：
- 是否使用 `get_logger(__name__)`
- 日志是否带关键上下文
- 失败路径是否可观测
- 新的关键流程是否需要 metrics / tracing / health 信号

要抓的典型问题：
- 只 `pass` 不记录
- 失败路径没有任何日志
- 新外部依赖没有 health check

### 3.4 DTO / Entity / ORM 职责混淆

检查：
- DTO 是否承担了业务逻辑
- entity 是否变成数据容器，没有规则
- ORM model 是否渗透到 API 或 application
- `model_validate(...from_attributes=True)` 的使用是否合理

### 3.5 测试缺口

检查：
- 是否只测 happy path
- 是否缺少未授权、越权、并发、重复请求、外部失败测试
- 是否缺少 application 层 fake port / fake repo 测试
- 是否缺少关键异常映射测试

最少应覆盖：
- 一个成功路径
- 一个业务错误路径
- 一个边界或失败路径

### 3.6 性能与资源使用

检查：
- 是否有明显 N+1
- 是否在 API 层做重计算或过多串行 await
- 是否缺少批量处理 / 限流 / semaphore
- 文件流、日志流、WebSocket 发送是否有背压上限

### 3.7 魔法值与重复实现

检查：
- 状态字符串、错误消息、默认 TTL、限流数值是否散落
- 同一类 header / permission / validation 是否重复实现
- 是否已经有现成 helper / adapter / base service 可复用

---

## 4. 仓库定制关注点

针对当前仓库，review 时要额外盯这些点：

### 4.1 文件访问默认匿名

当前文件相关接口里已有多处：
- `user_id=None`
- `No permission check`

后续任何扩展如果继续沿用这一模式，默认要判为高风险，除非这是明确的公开资源设计。

### 4.2 UoW 仍偏单聚合

如果新增聚合时继续把具体 repository 硬编码进通用 UoW，要提醒这是“样例骨架扩张”，不是“真正通用化”。

### 4.3 外部能力有配置但未完全落地

例如：
- rate limit
- sentry
- 邮件
- 某些 observability 能力

review 时要警惕“只有配置，没有执行路径”的假能力。

### 4.4 Best-effort 异常吞掉

如果代码里继续出现：

```python
except Exception:
    pass
```

需要区分：
- 这是幂等语义下可接受的降级
- 还是把真实错误静默吞掉

前者至少要有日志或注释说明理由；后者应判问题。

---

## 5. 不建议乱报的问题

以下问题默认不要作为 review finding：
- 纯风格偏好但不影响结构和行为
- “可以更优雅”但没有明确风险
- 与现有仓库模式一致的轻微重复
- 没有结合本仓库 DDD 约束的泛泛而谈

原则：
- 优先报会导致 bug、回归、安全问题、分层破坏、测试缺口的问题
- 少报审美型意见，多报结构型风险

---

## 6. 推荐结论级别

### Blocking
- 分层违规
- 权限缺失
- 并发 / 幂等错误
- 事务与 side effect 不一致
- 未校验外部输入直接入库
- 关键安全问题

### Non-blocking
- 异常/日志/DTO 一致性问题
- 测试不足但已有基础覆盖
- 性能与复用建议
- 魔法值、重复代码、命名问题

---

## 7. 最小审查清单

如果时间非常有限，至少回答这 7 个问题：

1. 有没有破坏 `API → application → domain ← infrastructure`？
2. 有没有资源越权或缺少权限检查？
3. 有没有并发 / 幂等 / 状态流转风险？
4. 有没有 DB 与外部 side effect 不一致窗口？
5. 有没有外部输入未校验直接入库？
6. 有没有只测 happy path？
7. 有没有把错误静默吞掉？

如果 7 个问题全过，这个改动通常至少具备基础可上线质量。
