# scripts/

脚本工具目录。

## 文件索引

| 文件 | 用途 |
|------|------|
| `run-epic.sh` | Epic 级 Story 自动化编排：解析 Epic markdown → 生成 Makefile DAG → 用 `claude -p` 逐个执行 |
| `check-story-result.sh` | Story 执行结果检查：解析 `claude -p` 的 JSON 输出，判断 done/blocked |

## run-epic.sh

从 Epic 文件自动编排所有 Story 的执行。核心思想：**Epic 文件即 Pipeline**。

### 工作原理

1. 解析 Epic markdown 中的 `### Story X.Y` 和 `**依赖**: ...`
2. 自动生成 Makefile，story 之间的依赖映射为 make prerequisites
3. 用 `make` 驱动执行，每个 story 调用 `claude -p "使用 run-story ..."` 在独立 session 中运行
4. 完成标记写入 `.epic-run/done/epic-N/X.Y`，重跑时自动跳过已完成的 story

### 用法

```bash
# 顺序执行整个 Epic
./scripts/run-epic.sh path/to/epic.md

# 无依赖的 story 最多 2 个并行
./scripts/run-epic.sh path/to/epic.md -j2

# 只生成 Makefile，不执行（检查依赖图）
./scripts/run-epic.sh path/to/epic.md --dry-run

# 从 story 1.3 开始（跳过前面的 story）
./scripts/run-epic.sh path/to/epic.md --from 1.3

# 只跑到 story 1.4（含其依赖链）
./scripts/run-epic.sh path/to/epic.md --target 1.4

# 查看各 story 完成状态
./scripts/run-epic.sh path/to/epic.md --status

# 清除某个 story 的完成标记，下次重跑
./scripts/run-epic.sh path/to/epic.md --reset 1.2
```

### 特性

- **幂等**：已完成的 story 自动跳过（基于 `.epic-run/done/` 标记文件）
- **断点续跑**：中断后重跑同一命令，从上次失败处继续
- **并行**：`-j2` 让无依赖关系的 story 同时执行
- **依赖图**：从 Epic 文件的 `**依赖**:` 行自动解析，支持跨 epic 依赖
- **Dry run**：`--dry-run` 生成并打印 Makefile，不实际执行

### 运行时目录

```
.epic-run/                    # gitignored，自动创建
├── Makefile.epic-1           # 自动生成的 DAG
├── done/epic-1/
│   ├── 1.1                   # 完成标记（touch 文件）
│   └── ...
└── logs/epic-1/
    ├── 1.1.log               # claude -p 完整输出
    └── ...
```

### 依赖关系示例（epic-1）

```
1.1 (无依赖)
├── 1.2 (← 1.1)
├── 1.3 (← 1.1) ──→ 1.4 (← 1.3)
├── 1.5 (← 1.1)
├── 1.6 (← 1.1)
└── 1.7 (← 1.1)
```

`-j3` 时：1.1 先跑 → 1.2/1.3/1.5 并行（最多 3 个）→ 1.4 等 1.3 完成后跑 → 1.6/1.7 补位。
