# 数据模型 · exam 模块

> 范围：业务资料、考试目标、知识点（Epic 2）。
> 全局持久化约定见 [overview.md](./overview.md)。API 契约见 [../api/exam.md](../api/exam.md)。

## 模块范围

| 聚合 | 表 | Domain 落点 |
|------|----|------------|
| 业务资料 | `materials` | `domain/exam_material/entity.py` |
| 考试目标 | `exam_objectives` | `domain/exam_objective/entity.py` |
| 知识点 | `knowledge_points` | `domain/exam_knowledge_point/entity.py` |

---

## ERD

```mermaid
erDiagram
    users ||--o{ materials : "created_by"
    users ||--o{ exam_objectives : "created_by"
    materials ||--o{ knowledge_points : "material_id"

    materials {
        int id PK
        text content NN
        varchar filename "nullable; 原始文件名"
        varchar status NN "固定='ready'(创建后不变)"
        int created_by FK,NN "-> users.id"
        datetime created_at NN
        datetime updated_at
        datetime deleted_at "软删除(SoftDeleteFilterMixin)"
    }

    exam_objectives {
        int id PK
        text target_object NN "考核对象"
        text purpose NN "考核目的"
        text knowledge_points_scope NN "覆盖知识点"
        text question_type_difficulty_score NN "题型难度分值"
        text out_of_scope "nullable; 不考核范围(可选)"
        text subjective_scoring_focus NN "主观题评分重点"
        int created_by FK,NN "-> users.id"
        datetime created_at NN
        datetime updated_at
    }

    knowledge_points {
        int id PK
        int material_id FK,NN "-> materials.id"
        varchar name NN "知识点名称"
        boolean confirmed NN "default=false; PUT 确认后=true"
        int sort_order "nullable; 展示排序"
        datetime created_at NN
        datetime updated_at
    }
```

---

## 表详情

### `materials`

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | INT | PK, AUTO | — |
| `content` | TEXT | NOT NULL | 资料全文（文本粘贴 or 文件内容） |
| `filename` | VARCHAR(255) | nullable | 原始文件名；文本粘贴时为 null |
| `status` | VARCHAR(20) | NOT NULL, default='ready' | MVP 固定值 'ready'；后续可扩展 |
| `extraction_status` | VARCHAR(20) | nullable | null/processing/completed/failed；知识点异步提取状态（FastAPI BackgroundTasks） |
| `extraction_task_id` | VARCHAR(255) | nullable | 历史遗留列（曾存 Celery task_id）；BackgroundTasks 下不再写入 |
| `created_by` | INT | FK→users.id, NOT NULL | 录入管理员 |
| `created_at` | DATETIME | NOT NULL | TimestampMixin |
| `updated_at` | DATETIME | nullable | TimestampMixin |
| `deleted_at` | DATETIME | nullable | 软删除（`SoftDeleteFilterMixin`） |

**索引**：`ix_materials_created_by`（created_by）；`ix_materials_status`（status）

### `material_chunks`

资料切块表：录入时由 `split_into_chunks` 切分 `materials.content` 持久化，供知识点提取
（map-reduce over chunks）与 grounded 出题（按 KP 名字面匹配选相关 chunk）共用。

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | INT | PK, AUTO | — |
| `material_id` | INT | FK→materials.id, NOT NULL | 所属资料 |
| `ordinal` | INT | NOT NULL | 切块顺序号，从 0 起 |
| `content` | TEXT | NOT NULL | 切块文本（≤max_chars，相邻块带 overlap 重叠） |
| `created_at` | DATETIME | NOT NULL | — |

**索引**：`ix_material_chunks_material_id_ordinal`（material_id, ordinal）

### `exam_objectives`

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | INT | PK, AUTO | — |
| `target_object` | TEXT | NOT NULL | 考核对象 |
| `purpose` | TEXT | NOT NULL | 考核目的 |
| `knowledge_points_scope` | TEXT | NOT NULL | 覆盖知识点 |
| `question_type_difficulty_score` | TEXT | NOT NULL | 题型/难度/分值要求 |
| `out_of_scope` | TEXT | nullable | 不考核范围（可选，见 D3） |
| `subjective_scoring_focus` | TEXT | NOT NULL | 主观题评分重点 |
| `created_by` | INT | FK→users.id, NOT NULL | 创建者 |
| `created_at` | DATETIME | NOT NULL | — |
| `updated_at` | DATETIME | nullable | — |

### `knowledge_points`

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | INT | PK, AUTO | — |
| `material_id` | INT | FK→materials.id, NOT NULL | 来源资料 |
| `name` | VARCHAR(500) | NOT NULL | 知识点名称 |
| `confirmed` | BOOLEAN | NOT NULL, default=false | true = 管理员已确认，可进入出题 |
| `sort_order` | INT | nullable | 前端展示排序 |
| `created_at` | DATETIME | NOT NULL | — |
| `updated_at` | DATETIME | nullable | — |

**索引**：`ix_knowledge_points_material_id`（material_id）；`ix_knowledge_points_confirmed`（confirmed）

---

## 不变量与一致性

- **0 条空知识点不变量**（R2.4）：`confirmed=false` 的知识点永远不被 Epic 3 消费；Epic 3 只调用 `GET .../knowledge-points?confirmed=true`。
- **全量替换一致性**（D4）：`PUT .../knowledge-points` 在单个 UoW 事务内 delete + bulk insert；操作前后 material 对应的 `confirmed=true` 行集合是原子切换。
- **外键级联**：`knowledge_points.material_id` ON DELETE CASCADE（或 application 层在 material 软删除时先清 KP）。
- **exam_objectives 无软删除**（MVP）：直接物理删除或仅通过 PUT 更新；Epic 3 引用时若 objective 已删则 application 层返回 404。

---

## Migration

Migration 文件：`alembic/versions/<rev>_add_exam_material_objective_knowledge_point.py`

运行顺序（创建）：
1. `materials`（依赖 `users`）
2. `exam_objectives`（依赖 `users`）
3. `knowledge_points`（依赖 `materials`）

回滚：`alembic downgrade -1`（按 FK 依赖顺序：先 drop `knowledge_points` → 再 drop `materials`/`exam_objectives`）

**新模型须在 `infrastructure/models/__init__.py` 导入**（`MaterialModel`、`ExamObjectiveModel`、`KnowledgePointModel`）才能被 Alembic autogenerate 发现。
