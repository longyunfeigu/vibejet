# Architecture Decision Records

This directory stores durable architecture decisions for `vibejet`.

Use an ADR when a decision is hard to infer from code alone or when future maintainers need the
context behind a tradeoff. Examples include dependency direction, runtime boundaries, persistence
patterns, workflow conventions, and toolchain choices.

## Naming

Use this format:

```text
NNNN-short-kebab-title.md
```

Example:

```text
0001-keep-domain-independent-from-infrastructure.md
```

## Suggested Sections

- Status
- Context
- Decision
- Consequences
- Alternatives Considered

## Index

- [0001 架构边界 + 编码红线上锁](0001-architecture-rule-locking.md) — import-linter 依赖方向契约 + flake8-print + UoW 形状测试的设计与被拒绝方案
