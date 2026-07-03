# Epic 1 决策记录（D/ACD 唯一真相源）

> 本 Epic 在无人值守模式下规划，以下决策标注为「假设待审批」+ Confidence，reviewer 不同意任一条时对应 Unit 需返工。

## D1: 越权响应统一 404，不用 403 【假设待审批 · Confidence: high】

非 owner 访问他人资源时，抛对应模块的 `*NotFoundException`（404），与访问不存在 ID 的表现完全一致。

**Why**: 403 会泄露"该 ID 存在但不属于你"，配合自增整数主键可被枚举遍历。404 是资源级越权的行业默认做法（GitHub 私有仓库同语义）。`BusinessCode.NOT_FOUND→404` 映射已存在，复用各模块既有 NotFound 异常，不新增异常类。
**Rejected**: 新增 `ForbiddenException(30002)→403` ——语义诚实但泄露存在性；留给未来"确实需要区分 401/403/404"的 RBAC epic。

## D2: 归属断言放 application service，签名用必填 `owner_id` 关键字参数 【假设待审批 · Confidence: high】

route-facing 服务方法增加**必填** `owner_id: int` 关键字参数；load 实体后用领域方法 `belongs_to(owner_id)` 断言；路由只负责传 `current_user.id`。不引入装饰器/中间件/通用 helper。

**Why**: `docs/project/api/conventions.md` 已约定"default-deny：在 application service 强制 owner 边界"。必填参数使"忘记传"变成 TypeError 而非静默放行（fail-closed）。检查本身只有两行，抽通用 helper 属过度抽象（仓库红线）。
**Rejected**: ① 可选参数 `owner_id: Optional[int]=None`（None=跳过检查）——默认开放，容易静默漏检；② FastAPI 依赖注入层做检查——路由层不该持有业务规则，且绕过 API 直调服务时失去保护；③ 通用 `ensure_owned()` helper——两行代码不值得一层抽象。
**内部调用边界**: 后台 worker（document `process_document`）、清理任务（purge/mark_active 系列）不走 route-facing 方法、直接用 repo，不加 owner 参数。

## D3: 本 Epic 无 superuser 越权通道 【假设待审批 · Confidence: medium】

`is_superuser` 用户与普通用户同规则——只能访问自己的资源。

**Why**: 当前没有任何 admin 界面/用例消费"管理员看全部"；先加通道等于埋一条没人测试的隐性权限路径（投机功能红线）。
**Rejected**: `if user.is_superuser: skip check` ——等真实 admin 需求出现时，随 RBAC epic 一起设计并测试。

## D4: conversations.owner_id 可空、不回填，NULL 视为孤儿 【假设待审批 · Confidence: high】

migration 0004 加可空列，不回填历史行。`belongs_to` 对 NULL owner 恒 False → 遗留行对所有用户不可见。

**Why**: 与 file_assets / documents 的既有形状一致（都是可空 owner_id）；本仓库是基础库，无生产数据，孤儿行只存在于开发库，无迁移风险。NOT NULL 需要虚构一个回填 owner，反而制造假数据。
**Rejected**: NOT NULL + 回填到某个系统用户——虚构归属，且下游项目各有各的回填策略，不该由基础库定死。

## D5: agent-configs 端点不在本 Epic 范围 【假设待审批 · Confidence: medium】

`/agent-configs` 5 个端点维持现状（仅登录闸门）。

**Why**: AgentConfig 无 owner 列，且"Agent 配置"更接近共享/租户级资源，归属语义未定义；加 owner 需要另一张表的 migration + 同样的全栈改造，超出"资源归属"epic 的清晰边界。
**Rejected**: 顺手给 agent_configs 也加 owner——范围膨胀，且共享配置按 owner 隔离可能根本是错误模型。
**风险披露**: 在 ownership 上线后，agent-configs 将是仅剩的"任何登录用户可改全局配置"端点，已在 conventions.md 鉴权段落明示。

## ACD-1: `CONVERSATION_NOT_FOUND` / `DOCUMENT_NOT_FOUND` 从 HTTP 400 改为 404 【行为变更 · Confidence: high】

这两个业务码不在 `core/exceptions.py` 的映射表中，当前落默认 400。本 Epic 把它们加入映射 → 404。

**影响面**: 对外可观测行为变更（红线要求显式披露）。检查过全部消费方：前端只有 auth + home 两个 feature，不消费这些端点；仓库内测试断言的是异常类型而非 HTTP 状态。业务码数值不变，按 `code` 判别的客户端不受影响。
**Why now**: 越权要伪装成"不存在"，若"真不存在"返回 400 而越权返回 404，反而制造了区分信号，D1 就失效了。两者必须同码。
