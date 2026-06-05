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

- [0001 LLM 结构化输出能力加在端口层](0001-llm-structured-output-at-port-layer.md) — `LLMPort.generate_structured` + 独立超时预算 + 失败边界两分（epic-3 D3/D4）
- [0002 文档驱动 grounded 出题](0002-grounded-doc-question-generation.md) — 切块 + map-reduce 提取（BackgroundTasks）+ 锚定原文出题 + 忠实闸（B1，不上向量库）
