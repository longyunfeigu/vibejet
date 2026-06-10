# documents 表

文档解析聚合的持久化模型。迁移：`backend/alembic/versions/20260610_0002_documents.py`（revision 0002）。
ORM：`backend/infrastructure/models/document.py`。

## 列

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | Integer | PK, autoincrement | 主键 |
| `owner_id` | Integer | nullable | 归属用户（逻辑外键，未强制约束，与 file_assets 一致） |
| `file_asset_id` | Integer | not null, index | 关联文件资产（逻辑外键） |
| `title` | String(255) | nullable | 标题，默认取原始文件名 |
| `source_filename` | String(255) | nullable | 原始文件名快照 |
| `content_type` | String(100) | nullable | 源文件 MIME 快照 |
| `parser` | String(32) | nullable | 完成解析所用解析器：markitdown/textin |
| `status` | String(20) | not null, default `'pending'` | pending/parsing/ready/failed |
| `content_md` | Text | nullable | 解析产物（规范化 Markdown），ready 时非空 |
| `error_code` | String(64) | nullable | 失败错误码（稳定标识，见 api/documents.md） |
| `error_message` | Text | nullable | 失败详情 |
| `metadata` | JSON | nullable | 扩展元数据（chars/pages 等；ORM 属性名 `extra_metadata`） |
| `created_at` / `updated_at` | DateTime(tz) | not null, server_default now() | 时间戳 |
| `deleted_at` | DateTime(tz) | nullable | 软删除标记 |

## 索引

- `ix_documents_created_at` (created_at)
- `ix_documents_owner_created` (owner_id, created_at)
- `ix_documents_file_asset_id` (file_asset_id)

## 设计决策

- `content_md` 存 DB Text 列而非对象存储：模板阶段最简、避免双写一致性；
  超大规模场景下游可迁移到对象存储 + 这里只存指针
- 不对 `file_asset_id`/`owner_id` 建 FK：沿用 file_assets 的既有约定（示例项目不强制外键）
- 解析产物是派生数据：源文件在即可通过 reparse 重建，无需备份策略
