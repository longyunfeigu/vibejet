# Data Contracts

Current foundation schema contracts:

- [document.md](document.md) — `documents` 表（文档解析聚合，migration 0002）

When a reusable platform schema becomes part of the foundation, document it in
this directory alongside the Alembic migration that creates it. Downstream
application schemas should live in the downstream project. Historical internal
exam-platform data contracts were archived under
`docs/archive/exam-platform/project/data/`.
