# Epic {N} {名称} — Execution Ledger

> Generated/appended by `vj-work`. **Append-only 执行账本**：task 状态、verification 结果与变更叙事的唯一落点。
> task 文档是纯投影（可整目录重写），执行记录只写这里。
> fast 与 strict 使用**同一 schema**，差别只在写入时机：strict 每 task 完成即 append 一个条目；
> fast 在 Phase 4 收尾统一 append 全部条目。不回改已写条目；纠错追加新条目并注明 supersedes。

## Status Board

| Task | Unit | Status | Verification | Commit |
|------|------|--------|--------------|--------|
| T001 | U1 | ☐ pending / ◐ in-progress / ☑ done / ⊘ skipped / ✗ blocked | {命令 exit code 或 -} | {SHA 或 -} |

## Entries

<!-- 每个 task 完成（strict）或收尾（fast）append 一个条目，格式固定如下： -->

### T{NNN} — {task 标题}（{done|skipped|blocked}, {date}）

- **实际做了什么**: {人话 3-5 句：建/改了什么、怎么工作}
- **怎么满足验收**: {逐条对应 AC / Verification；skipped/blocked 写原因}
- **关键权衡 / 偏离**: {为什么这么选；偏离 task packet / Unit Packet 之处及原因；无则"无"}
- **验证结果**: {Verification 命令 + 关键输出摘要；Unit 收口 task 附 `verify.sh {U-ID}` 输出摘要}
- **Commit / 关键文件**: {SHA + 文件列表}

### Unit 收口 — U{N}（{date}）

- **Unit Verification**: {`verify.sh U{N}` 结果 + Story AC 核对结论}
- **Sibling tasks**: {T-ID 列表及状态}
