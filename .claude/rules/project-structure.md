<!-- input: 仓库目录结构与各层 README -->
<!-- output: 核心目录导航索引（@README 引用） -->
<!-- pos: 结构导览入口（架构规则统一在 AGENTS.md，本文件只做 README 索引）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md -->

---
paths:
  - "**/*"
---

# 项目结构导航

本项目采用 **DDD + 六边形架构**。依赖方向、层级职责与架构约束统一见 AGENTS.md 的
Backend Architecture 节（本文件不重复维护）。理解项目时优先从下列核心目录 README 开始阅读。

## 核心目录索引

### 后端（Python）

- @backend/README.md - 后端根目录：入口、运行方式与分层概览
- @backend/domain/README.md - 领域层：纯业务逻辑、实体、仓储接口
- @backend/application/README.md - 应用层：用例编排、DTO、端口定义
- @backend/infrastructure/README.md - 基础设施层：数据库/外部服务/仓储实现
- @backend/api/README.md - 表示层：HTTP 路由、中间件、依赖注入
- @backend/core/README.md - 共享基础设施：配置、日志、异常、响应、国际化
- @backend/shared/README.md - 跨切面工具：业务码、常量、提示词等
- @backend/grpc_app/README.md - gRPC 服务：proto、拦截器、服务实现
- @backend/alembic/README.md - 数据库迁移：版本管理与常用命令
- @backend/locales/README.md - 国际化：翻译源文件（.po）与编译流程
- @backend/tests/README.md - 后端测试：fixture、路由与服务测试
- @backend/scripts/README.md - 脚本工具：proto 生成、Celery 启动等
- @backend/static/README.md - 静态资源：样例/模板文件

### 文档（Markdown）

- @docs/README.md - 设计与使用文档索引

### 前端

- @frontend/README.md - 前端目录当前状态与约定
