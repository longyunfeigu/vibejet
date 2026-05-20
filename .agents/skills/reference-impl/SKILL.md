---
name: reference-impl
description: 参考开源项目实现功能。结构化研究参考源码/文档，提取核心设计，适配本项目 DDD 架构后实现。
---

# reference-impl - 借助开源项目实现功能

通过结构化的"研究 → 提取 → 适配 → 实现"流程，将开源项目的设计思路转化为符合本项目架构的实现。

**角色定位**：技术研究员 + 架构适配器。先深度理解参考实现的 **Why**（为什么这样设计），再提取 **What**（核心抽象和数据结构），最后适配 **How**（在本项目中如何落地）。

---

## Phase 0: 初始化 — 解析意图 & 选择研究方法

### Step 1: 解析用户输入

从用户输入中提取三个关键信息：

```
┌─────────────────────────────────────────────────────┐
│  输入解析                                            │
│                                                      │
│  1. 目标功能：我想实现什么？                          │
│     → 提取功能描述、期望行为、约束条件                │
│                                                      │
│  2. 参考来源：参考谁的实现？                          │
│     → 项目名 / GitHub URL / 库名 / "不确定"          │
│                                                      │
│  3. 参考粒度：参考到什么程度？                        │
│     → 整体架构 / 单个模块 / 某个API用法 / 设计思路    │
└─────────────────────────────────────────────────────┘
```

如果用户输入不完整，使用 AskUserQuestion 补全：

```
问题1 [目标功能]: 你想实现什么功能？请描述期望行为。
问题2 [参考来源]: 参考哪个开源项目？
  - 具体项目（提供名称或 GitHub URL）
  - 某个库的功能（提供库名 + 功能名）
  - 不确定，需要搜索推荐
问题3 [参考粒度]: 你想参考到什么程度？
  - 整体架构设计（模块划分、数据流、扩展点）
  - 单个模块的实现逻辑（算法、状态管理、并发处理）
  - 某个 API/协议的用法（接口调用方式）
  - 只要设计思路，实现细节自己来
```

### Step 2: 选择研究方法

根据解析结果，按以下决策树选择：

```
参考来源是什么？
│
├─ 主流库/框架的 API 用法 (FastAPI, React, LangChain, etc.)
│  → 方法 A: Context7 查文档
│
├─ 具体 GitHub 项目 + 已知文件路径
│  ├─ 文件数 ≤ 3 → 方法 D: gh CLI 读单文件
│  └─ 文件数 > 3 → 方法 C: Clone 到本地
│
├─ 具体 GitHub 项目 + 不知道具体文件
│  → 方法 B: WebSearch 定位 + WebFetch 读源码
│
├─ 知道项目名但没有 URL
│  → 方法 B: WebSearch 搜索项目 + 定位源码
│
└─ 不确定参考谁
   → 方法 E: 多项目对比选型
```

输出决策：
```
研究策略:
- 目标功能: {功能描述}
- 参考项目: {项目名}
- 参考粒度: {粒度}
- 研究方法: 方法{X} - {方法名}
- 预期关注点:
  1. {关注点1}
  2. {关注点2}
  3. {关注点3}

确认开始研究？
```

**GATE: 等待用户确认研究策略后再进入 Phase 1。**

---

## Phase 1: 研究参考实现 — 只研究，不写代码

**硬约束：本 Phase 不输出任何实现代码，只输出研究报告。**

### 方法 A: Context7 查文档

**使用场景**：参考的是主流库/框架的功能用法

**执行步骤**：
```
1. 调用 mcp__context7__resolve-library-id
   → 输入: 库名 (如 "fastapi", "langchain")
   → 获取: library ID

2. 调用 mcp__context7__query-docs
   → 输入: library ID + 具体功能关键词
   → 获取: 相关文档和示例代码

3. 如果文档不够完整:
   → 补充 WebSearch 搜索 "{库名} {功能} example/tutorial 2025/2026"
   → WebFetch 阅读最相关的 2-3 个链接
```

**输出模板**：
```markdown
### 研究报告: {库名} - {功能名}

#### 1. 官方推荐用法
- API 签名: `{函数/类签名}`
- 核心参数:
  | 参数 | 类型 | 作用 | 默认值 |
  |------|------|------|--------|
  | ... | ... | ... | ... |
- 最小可用示例:
  ```python
  {示例代码，来自文档}
  ```

#### 2. 设计意图
- 这个 API 解决什么问题: {问题描述}
- 为什么这样设计（而非其他方式）: {设计理由}
- 官方文档中提到的注意事项/陷阱: {注意事项}

#### 3. 高级用法（如适用）
- 自定义/扩展方式: {扩展点}
- 与其他组件的集成模式: {集成方式}

#### 4. 版本兼容性
- 当前稳定版本: {版本号}
- 此功能引入版本: {版本号}
- Breaking changes 警告: {如有}
```

### 方法 B: WebSearch + WebFetch 读源码

**使用场景**：参考具体项目的实现逻辑，但不确定具体文件位置

**执行步骤**：
```
1. WebSearch 定位源码位置
   搜索词组合策略（按优先级尝试）:
   a. "{项目名} {功能关键词} source code implementation"
   b. "{项目名} github {模块名}"
   c. "site:github.com/{owner}/{repo} {功能关键词}"

2. WebFetch 阅读关键文件 (限制 ≤ 5 个文件)
   优先级:
   a. 入口文件 / 主逻辑文件
   b. 核心数据结构 / 模型定义
   c. 接口定义 / 抽象类

3. 如果 WebFetch 内容被截断或不完整:
   → 切换到方法 D (gh CLI) 读取完整文件
```

### 方法 C: Clone 到本地读源码

**使用场景**：需要理解复杂架构全貌，涉及 >3 个文件

**执行步骤**：
```
1. Clone 参考项目
   git clone --depth 1 --single-branch {repo_url} /tmp/ref-{project_name}

2. 目录结构分析
   ls -la /tmp/ref-{project_name}/
   → 识别项目组织方式（monorepo? 分层? 按功能?）

3. 入口定位
   → 找到功能入口文件（搜索关键词、读 README）
   → 从入口出发，追踪调用链

4. 分层阅读（按调用链深度，限制 ≤ 10 个文件）
   Layer 1: 入口/路由/API 定义
   Layer 2: 业务逻辑/服务层
   Layer 3: 数据模型/存储层
   Layer 4: 辅助工具/配置

5. 清理
   rm -rf /tmp/ref-{project_name}
```

### 方法 D: gh CLI 读单文件

**使用场景**：已知具体文件路径，只需读 1-3 个文件

**执行步骤**：
```
1. 确认仓库可访问
   gh api repos/{owner}/{repo} --jq '.full_name'

2. 如果不知道确切路径，先搜索
   gh api search/code -f q="{关键词} repo:{owner}/{repo}" --jq '.items[].path'

3. 读取文件内容
   gh api repos/{owner}/{repo}/contents/{path} --jq '.content' | base64 -d

4. 如果文件 >1MB，改用 raw URL
   gh api repos/{owner}/{repo}/contents/{path} --jq '.download_url' | xargs curl -s
```

### 方法 E: 多项目对比选型

**使用场景**：不确定参考哪个项目，需要先选型

**执行步骤**：
```
1. WebSearch 搜索候选项目
   搜索词: "{功能描述} open source python/typescript 2025/2026"
   搜索词: "{功能描述} github stars"

2. 筛选 Top 3 候选（筛选标准）:
   - GitHub Stars > 500
   - 最近 6 个月有 commit
   - 文档/README 质量
   - 技术栈兼容性 (Python/FastAPI 优先)

3. 对每个候选快速研究（方法 B 或 D）:
   - 读 README 了解架构
   - 读核心模块 1-2 个文件了解实现质量

4. 输出对比表，推荐最佳候选
```

### 研究报告统一输出格式

**无论使用哪种方法，Phase 1 结束时必须输出以下格式的报告**：

```markdown
## 研究报告: {参考项目} — {功能名}

### 1. 架构概览
- 参考项目的整体架构风格: {单体/微服务/插件式/...}
- 此功能所在的模块层级: {模块路径}
- 模块间依赖关系:
  ```
  {ASCII 依赖图或简要描述}
  ```

### 2. 核心设计决策
| # | 决策点 | 参考项目的选择 | 选择理由 | 备选方案 |
|---|--------|---------------|----------|----------|
| 1 | {决策点} | {选择} | {理由} | {备选} |
| 2 | ... | ... | ... | ... |

### 3. 关键数据结构
```python
# 从参考项目中提取的核心数据模型（用 Python 伪代码表示）
class {CoreModel}:
    {field}: {type}  # {说明}
    ...
```

### 4. 核心流程
```
{用 ASCII 流程图描述核心业务流程}
例如:
用户请求 → 验证 → 创建任务 → 异步执行 → 回调通知
              ↓ (失败)
           返回错误
```

### 5. 接口/抽象定义
```python
# 参考项目定义的关键接口/抽象基类
class {InterfaceName}(Protocol):
    def {method}(self, {params}) -> {return_type}:
        """说明"""
        ...
```

### 6. 值得借鉴的点
- {值得借鉴的设计1}: {为什么好}
- {值得借鉴的设计2}: {为什么好}

### 7. 不适合直接复用的点
- {不适合的点1}: {原因} → 我们的替代方案: {方案}
- {不适合的点2}: {原因} → 我们的替代方案: {方案}

### 8. 参考文件索引
| 文件路径 | 作用 | 关键行/函数 | 参考价值 |
|----------|------|-------------|----------|
| {path} | {描述} | {line range / function name} | 高/中/低 |
```

**GATE: 输出报告后，等待用户确认理解是否正确，再进入 Phase 2。**

---

## Phase 2: 适配设计 — 映射到本项目 DDD 架构

**硬约束：本 Phase 不输出实现代码，只输出设计方案。**

### Step 1: 读取项目架构约束

```
必读文件:
- CLAUDE.md → 分层规则、依赖方向
- docs/project/architecture.md → 架构决策（如存在）
- docs/project/api_spec.md → API 规范（如存在）
- docs/project/database_schema.md → 数据模型（如存在）

提取约束:
- 依赖方向: API → Application → Domain ← Infrastructure
- Domain 层禁止: 不导入 infrastructure/application/api
- Infrastructure 层: 必须实现 Domain 定义的接口
- Application 层: 不直接使用 ORM Model
```

### Step 2: 概念映射

将参考项目的概念映射到本项目的 DDD 分层：

```markdown
### 概念映射表

| 参考项目的概念 | 参考项目的位置 | → 本项目的 DDD 层 | 本项目的文件路径 | 映射方式 |
|---------------|---------------|-------------------|-----------------|---------|
| {Model} | {ref_path} | Domain 实体 | backend/domain/{module}/entity.py | 重新设计 |
| {Service} | {ref_path} | Application 服务 | backend/application/services/{x}_service.py | 改造复用 |
| {Repository} | {ref_path} | Domain 接口 + Infra 实现 | backend/domain/{module}/repository.py + backend/infrastructure/repositories/{x}_repository.py | 拆分 |
| {Handler} | {ref_path} | API 路由 | backend/api/routes/{x}.py | 重写 |
| {Config} | {ref_path} | Core 配置 | backend/core/config.py | 合并 |
```

映射方式说明:
- **直接复用**: 概念和实现都可以直接搬过来
- **改造复用**: 概念一致，但实现需要适配我们的接口/框架
- **重新设计**: 只借鉴思路，实现从零开始
- **拆分**: 参考项目的一个组件需要拆分到我们的多个层
- **合并**: 参考项目的多个组件在我们这里合并为一个
- **不需要**: 参考项目有但我们不需要的部分

### Step 3: 差异分析

```markdown
### 架构差异与适配策略

| 差异点 | 参考项目 | 本项目 | 适配策略 |
|--------|---------|--------|---------|
| 架构风格 | {参考的风格} | DDD + 六边形 | {如何适配} |
| ORM | {参考的ORM} | SQLAlchemy async | {如何适配} |
| 依赖注入 | {参考的方式} | FastAPI Depends | {如何适配} |
| 错误处理 | {参考的方式} | BusinessException | {如何适配} |
| ... | ... | ... | ... |
```

### Step 4: 输出实现方案

```markdown
### 实现方案

#### 文件变更清单

| 序号 | 操作 | 文件路径 | 说明 | 参考来源 |
|------|------|----------|------|----------|
| 1 | 新建 | backend/domain/{module}/entity.py | {实体} | 参考 {ref_file}:{line} |
| 2 | 新建 | backend/domain/{module}/repository.py | {仓储接口} | 自行设计 |
| 3 | 新建 | backend/application/services/{x}_service.py | {应用服务} | 参考 {ref_file}:{line} |
| 4 | 新建 | backend/infrastructure/repositories/{x}_repository.py | {仓储实现} | 参考 {ref_file}:{line} |
| 5 | 新建 | backend/api/routes/{x}.py | {API 路由} | 自行设计 |
| 6 | 修改 | backend/main.py | 注册路由 | - |

#### 实现顺序

```
1. Domain 层 (纯业务逻辑，无外部依赖)
   ├── entity.py: {实体类名}, {核心方法}
   └── repository.py: {接口名}, {方法签名}

2. Application 层 (用例编排)
   ├── services/{x}_service.py: {服务类名}
   └── dto.py: {DTO 类名} (如需要)

3. Infrastructure 层 (技术实现)
   ├── repositories/{x}_repository.py: 实现 Domain 接口
   └── models/{x}.py: ORM Model (如需要)

4. API 层 (HTTP 入口)
   ├── routes/{x}.py: {路由定义}
   └── dependencies.py: {依赖注入} (如需要)
```

#### 关键接口设计（伪代码）

```python
# Domain - 实体
class {Entity}:
    """从参考项目的 {RefModel} 适配而来"""
    {field}: {type}

    def {business_method}(self) -> {type}:
        """参考: {ref_file}:{line} 的 {ref_method}"""
        ...

# Domain - 仓储接口
class {Repository}(Protocol):
    async def {method}(self, {params}) -> {return_type}: ...

# Application - 服务
class {Service}:
    def __init__(self, repo: {Repository}):
        ...
    async def {use_case}(self, dto: {DTO}) -> {return_type}:
        """参考: {ref_file}:{line} 的 {ref_function}"""
        ...
```
```

**GATE: 输出方案后，等待用户确认，再进入 Phase 3。**

---

## Phase 3: 实现

**确认后才执行**。按 Phase 2 的方案和顺序实现。

遵循项目现有的开发规范：
- TDD 流程（如适用）：Red → Green → Refactor
- 每个 DDD 层完成后 commit
- 文件头部注释（遵循 doc-maintenance 规则）
- DDD 合规检查

---

## 重要规则

1. **Phase 1 和 Phase 2 不写实现代码** — 只输出研究报告和设计方案
2. **每个 Phase 结束有 GATE** — 等待用户确认再继续
3. **研究报告必须有"不适合直接复用"章节** — 防止盲目搬运
4. **概念映射表必须标注映射方式** — 明确哪些是直接复用、哪些要重新设计
5. **实现代码必须注释参考来源** — 关键函数标注 "参考: {project} {file}:{line}"
6. **不要照搬代码** — 理解设计意图后，用本项目的风格重写

---

## 示例交互

**用户**：`/reference-impl` 我想实现 Agent 执行过程中的流式日志输出。OpenHands 有类似的实现。

**Skill 响应**（Phase 0）：
```
已解析你的需求:

- 目标功能: Agent 执行过程中的流式日志输出
- 参考项目: OpenHands (github.com/All-Hands-AI/OpenHands)
- 参考粒度: 待确认

你想参考到什么程度？
□ 整体架构设计 — 事件系统的完整架构（模块划分、事件总线、传输层）
□ 单个模块逻辑 — 只看事件流推送部分（SSE/WebSocket 实现）
□ 设计思路即可 — 了解核心概念，实现自己来

另外，你特别关注哪些方面？（可多选）
□ 事件如何从 Agent 进程传递到前端
□ 事件的数据结构设计
□ 断线重连和历史事件回放
□ 流式输出的性能和背压处理
```
