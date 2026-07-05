# scripts/

仓库级脚本工具目录。当前没有活跃脚本。

## Epic / Story 执行

现行方式：`vj-epic-plan` 生成 task packets → `vj-work` 编排执行（自带波次并行、
worktree 隔离与 verify/review gate），不再依赖外部 shell 编排脚本。

> 早期的 `run-epic.sh` / `check-story-result.sh`（基于已移除的 `run-story` skill 的
> shell DAG 编排）已随该 skill 一并删除。
>
> 曾短暂存在的 `check_file_headers.py`（文件头注释 pre-commit gate）已随
> `.claude/rules/doc-maintenance.md` 规则本身一起移除——第一性原理复盘认定该规则维护的是
> 可从代码推导的冗余信息，弊大于利。复盘结论见
> `docs/reference/guides/base-library-principles.md`。
