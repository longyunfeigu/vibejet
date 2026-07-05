# Data Contracts

Current foundation schema contracts:

- [document.md](document.md) — `documents` 表（文档解析聚合）
- [conversation.md](conversation.md) — `conversations` 等对话聚合表（含归属列）
- [meal-log.md](meal-log.md) — `meal_records` / `meal_record_items`（饮食记录聚合，Epic 1，planned）

All tables are created by the single init migration `0001`
(`backend/alembic/versions/20260704_0001_init.py`).

When a reusable platform schema becomes part of the foundation, document it in
this directory alongside the Alembic migration that creates it. Downstream
application schemas should live in the downstream project.
