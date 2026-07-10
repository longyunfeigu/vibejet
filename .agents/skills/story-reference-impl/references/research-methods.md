# 参考实现研究方法工具箱（story-reference-impl Phase 0/1 用）

> SKILL.md 定阶段骨架与输出格式，本文件是研究方法的操作手册。
> 原 `reference-impl` skill 的方法部分并入此处（该 skill 已删除，本文件是唯一副本）。

## 方法选择决策树

```
参考来源是什么？
│
├─ 主流库/框架的 API 用法 (FastAPI, React, LangChain, ...)
│  → 方法 A: 官方文档优先
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

## 方法 A：官方文档优先

场景：参考的是主流库/框架的功能用法。

1. Context7 MCP 可用时：`resolve-library-id` → `query-docs`（库名 + 功能关键词）。
2. Context7 不可用或文档不全：WebSearch `"{库名} {功能} docs / example / tutorial 2026"`，
   WebFetch 阅读最相关的 2-3 个链接（官方文档优先于博客）。
3. 产出关注：API 签名与核心参数、最小可用示例、设计意图与官方陷阱提示、
   当前稳定版本与 breaking changes。

## 方法 B：WebSearch 定位 + WebFetch 读源码

场景：参考具体项目的实现逻辑，但不确定文件位置。

1. 搜索词按优先级：`"{项目名} {功能关键词} source code implementation"` →
   `"{项目名} github {模块名}"` → `"site:github.com/{owner}/{repo} {功能关键词}"`。
2. WebFetch 阅读关键文件（≤5 个），优先级：入口/主逻辑 → 核心数据结构/模型 →
   接口定义/抽象类。
3. 内容被截断或不完整 → 切方法 D（gh CLI）读完整文件。

## 方法 C：Clone 到本地读源码

场景：需要理解复杂架构全貌，涉及 >3 个文件。

```bash
git clone --depth 1 --single-branch {repo_url} /tmp/ref-{project}
ls /tmp/ref-{project}/            # 识别组织方式：monorepo / 分层 / 按功能
# 从 README + 关键词定位功能入口，沿调用链分层阅读（≤10 个文件）：
#   L1 入口/路由/API 定义 → L2 业务逻辑/服务 → L3 数据模型/存储 → L4 工具/配置
rm -rf /tmp/ref-{project}         # 研究完清理
```

## 方法 D：gh CLI 读单文件

场景：已知具体文件路径，只需读 1-3 个文件。

```bash
gh api repos/{owner}/{repo} --jq '.full_name'                       # 确认可访问
gh api search/code -f q="{关键词} repo:{owner}/{repo}" --jq '.items[].path'  # 不知路径先搜
gh api repos/{owner}/{repo}/contents/{path} --jq '.content' | base64 -d      # 读内容
# 文件 >1MB：--jq '.download_url' | xargs curl -s
```

## 方法 E：多项目对比选型

场景：不确定参考哪个项目，需要先选型。

1. WebSearch：`"{功能描述} open source {python|typescript} 2026"`、`"{功能描述} github"`。
2. 初筛 Top 3 候选，标准：
   - 维护活跃：近 6 个月有 commit
   - 社区规模：stars / 下载量（参考线 stars > 500，小众领域可放宽但须注明）
   - license 可商用：MIT / Apache-2.0 / BSD 优先；GPL 系标红，不明 license 不得直接引入
   - 技术栈契合：后端 Python / FastAPI / SQLAlchemy async；前端 React 19 / TS / Tailwind / shadcn
   - 文档 / README 质量
3. 每个候选快速研究（方法 B 或 D）：读 README 了解架构 + 读 1-2 个核心模块看实现质量。
4. 输出对比表并给出推荐与拒因。

> 与 vj-epic-plan Agent E（external-solutions scout）的分工：Agent E 在 plan-time 做
> 轻量选型（不 clone、只读 README 级），回答"用/改造/自研"；本 skill 在实现期做深度研究
> （可 clone、读调用链），回答"具体怎么改造"。
