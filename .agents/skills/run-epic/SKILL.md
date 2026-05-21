---
name: run-epic
description: 从 Epic 文件自动编排所有 Story 的顺序执行。解析 Epic markdown 中的 story 列表和依赖关系，生成 Makefile DAG，用 claude -p headless 模式逐个执行 run-story。支持断点续跑、并行、状态查看。
---

# run-epic

从 Epic 文件自动编排 Story 执行。核心思想：**Epic 文件即 Pipeline**。

## 适用场景

- 用户想批量执行一个 Epic 下的所有 Story
- 用户说"跑这个 epic""执行 epic-1""把 epic 1 的 story 都跑了"
- 用户想查看某个 epic 的 story 完成状态

## 不适用场景

- 只跑单个 Story → 用 `run-story`
- 还没有 Epic 文件 → 先用 `vj-epic-story`

## 工作原理

1. 解析 Epic markdown，提取所有 `### Story X.Y` 和 `**依赖**: ...`
2. 自动生成 Makefile，每个 story 是一个 target，依赖关系映射为 make prerequisites
3. 用 `make` 执行，每个 story 调用 `claude -p "使用 run-story ..."` 在独立 session 中运行
4. 完成的 story 用 `.epic-run/done/epic-N/X.Y` 标记文件跟踪，重跑时自动跳过

## 命令

所有操作通过 `scripts/run-epic.sh` 执行：

```bash
# 顺序执行整个 epic
./scripts/run-epic.sh docs/tasks/epics/epic-1-infrastructure.md

# 最多 2 个 story 并行（无依赖的 story 同时跑）
./scripts/run-epic.sh docs/tasks/epics/epic-1-infrastructure.md -j2

# 只生成 Makefile，不执行（检查依赖图是否正确）
./scripts/run-epic.sh docs/tasks/epics/epic-1-infrastructure.md --dry-run

# 从 story 1.3 开始（1.1, 1.2 标记为已完成并跳过）
./scripts/run-epic.sh docs/tasks/epics/epic-1-infrastructure.md --from 1.3

# 只跑到 story 1.4（含其依赖链）
./scripts/run-epic.sh docs/tasks/epics/epic-1-infrastructure.md --target 1.4

# 查看完成状态
./scripts/run-epic.sh docs/tasks/epics/epic-1-infrastructure.md --status

# 重置某个 story（清除完成标记，下次重跑）
./scripts/run-epic.sh docs/tasks/epics/epic-1-infrastructure.md --reset 1.2
```

## Workflow

当用户要求执行 epic 时：

1. 确认 Epic 文件路径
2. 询问是否需要特殊选项（并行、起始 story、dry-run）
3. 执行 `scripts/run-epic.sh`
4. 监控输出，向用户报告进度和结果

## 关键特性

| 特性 | 说明 |
|------|------|
| **幂等** | 已完成的 story 自动跳过（基于标记文件） |
| **断点续跑** | 中断后重跑，从上次失败处继续 |
| **并行** | `-j2` 无依赖的 story 自动并行 |
| **依赖图** | 从 Epic 文件的 `**依赖**:` 行自动解析 |
| **跨 epic 依赖** | 检查其他 epic 的完成标记，缺失时失败 |
| **Dry run** | `--dry-run` 只生成 Makefile 不执行 |

## 运行时目录

```
.epic-run/                    # gitignored
├── Makefile.epic-1           # 自动生成的 DAG
├── done/epic-1/
│   ├── 1.1                   # 完成标记
│   └── ...
└── logs/epic-1/
    ├── 1.1.log               # 完整 claude 输出
    └── ...
```

## 与其他 skill 的关系

- 内部调用 `run-story` 执行每个 story
- 上游：`vj-epic-story` 生成 Epic 文件
- 平级：`run-story` 处理单个 story
