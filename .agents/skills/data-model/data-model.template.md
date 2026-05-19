# [项目名称] 数据模型设计文档

> 本文档通过协作式对话生成，描述系统的数据模型设计。
>
> **生成时间**：[YYYY-MM-DD]
> **版本**：v1.0
> **模式**：[快速/标准/完整]

---

## 目录

1. [数据模型概述](#1-数据模型概述) `[必填]`
   - 1.1 [设计原则](#11-设计原则)
   - 1.2 [数据库选型](#12-数据库选型)
   - 1.3 [命名规范](#13-命名规范)
2. [聚合根设计](#2-聚合根设计) `[标准+]`
   - 2.1 [聚合根清单](#21-聚合根清单)
   - 2.2 [聚合根边界](#22-聚合根边界)
   - 2.3 [聚合根生命周期](#23-聚合根生命周期)
3. [实体关系图](#3-实体关系图) `[必填]`
   - 3.1 [ER 图](#31-er-图)
   - 3.2 [关系说明](#32-关系说明)
4. [表结构设计](#4-表结构设计) `[必填]`
   - 4.1 [模块A] 表结构(#41-模块a-表结构)
   - 4.2 [模块B] 表结构(#42-模块b-表结构)
5. [索引设计](#5-索引设计) `[标准+]`
   - 5.1 [索引清单](#51-索引清单)
   - 5.2 [索引策略](#52-索引策略)
6. [数据一致性](#6-数据一致性) `[标准+]`
   - 6.1 [并发控制](#61-并发控制)
   - 6.2 [事务边界](#62-事务边界)
   - 6.3 [约束设计](#63-约束设计)
7. [迁移规划](#7-迁移规划) `[完整]`
   - 7.1 [迁移脚本](#71-迁移脚本)
   - 7.2 [数据迁移策略](#72-数据迁移策略)
   - 7.3 [演进规则](#73-演进规则)
8. [附录](#8-附录) `[必填]`
   - 8.1 [术语表](#81-术语表)
   - 8.2 [变更日志](#82-变更日志)

---

## 1. 数据模型概述 `[必填]`

### 1.1 设计原则

本数据模型遵循以下核心设计原则：

| 原则 | 说明 | 实践方式 |
|------|------|----------|
| **单一职责** | 每张表只负责一个业务实体 | 避免大而全的宽表 |
| **数据一致性** | 通过约束保证数据完整性 | 外键、CHECK 约束、触发器 |
| **性能优先** | 索引设计支持高频查询 | 为 WHERE/JOIN/ORDER BY 建索引 |
| **可扩展性** | 支持业务增长和演进 | 预留扩展字段、软删除支持 |
| **规范化** | 遵循数据库范式原则 | 消除数据冗余、避免更新异常 |

**特殊设计决策**：
- [决策1]：[说明理由]
- [决策2]：[说明理由]

### 1.2 数据库选型

#### 主数据库

| 属性 | 选型 |
|------|------|
| **数据库** | `[PostgreSQL/MySQL/MongoDB/其他]` |
| **版本** | `[具体版本]` |
| **选型理由** | `[说明选型理由]` |

#### 存储与缓存

| 组件 | 选型 | 用途 |
|------|------|------|
| **缓存** | `[Redis/Memcached]` | [热点数据缓存] |
| **消息队列** | `[RabbitMQ/Kafka/无]` | [异步处理] |
| **对象存储** | `[S3/OSS/MinIO]` | [文件存储] |

#### 字段类型映射

根据选定的数据库，使用以下字段类型映射：

| 逻辑类型 | [PostgreSQL/MySQL/MongoDB] | 说明 |
|----------|---------------------------|------|
| 主键 | `[UUID/BIGINT/ObjectId]` | [说明] |
| 字符串 | `[VARCHAR(n)/TEXT/String]` | [说明] |
| 整数 | `[INTEGER/INT/NumberInt]` | [说明] |
| 大整数 | `[BIGINT/NumberLong]` | [说明] |
| 小数 | `[DECIMAL(p,s)/Decimal]` | [说明] |
| 布尔 | `[BOOLEAN/TINYINT(1)/Boolean]` | [说明] |
| 日期 | `[DATE/Date]` | [说明] |
| 时间 | `[TIMESTAMP/DATETIME/Date]` | [说明] |
| JSON | `[JSONB/JSON/Object]` | [说明] |
| 枚举 | `[ENUM/VARCHAR/String]` | [说明] |

### 1.3 命名规范

#### 表名规范

- 使用 **[snake_case/camelCase/PascalCase]** 格式
- 表名使用 **[单数/复数]** 形式
- 表名格式：`[模块前缀]_[实体名称]` 或 `[其他规则]`
- 关联表命名：`[table1]_[table2]` 或 `[其他规则]`

#### 字段名规范

| 字段类型 | 命名规范 | 示例 |
|----------|----------|------|
| 主键 | `[id/uuid]` | `id`, `user_id` |
| 外键 | `[关联表]_[主键]` | `user_id`, `order_id` |
| 布尔 | `is_[形容词]` 或 `has_[名词]` | `is_active`, `has_verified` |
| 时间戳 | `[action]_at` | `created_at`, `updated_at` |
| 创建人/更新人 | `[action]_by` | `created_by`, `updated_by` |
| 软删除 | `deleted_at` | `deleted_at` |
| JSON 字段 | `_config` 或 `_data` 后缀 | `llm_config`, `metadata` |

#### 索引名规范

- 主键索引：`PRIMARY KEY`
- 唯一索引：`uniq_[表名]_[字段名]`
- 普通索引：`idx_[表名]_[字段名]`
- 复合索引：`idx_[表名]_[字段1]_[字段2]`

---

## 2. 聚合根设计 `[标准+]`

> 本节基于 DDD（领域驱动设计）方法，识别系统的聚合根及其边界。

### 2.1 聚合根清单

基于业务模块划分，识别以下聚合根：

| 业务模块 | 聚合根 | 核心字段 | 聚合类型 | 说明 |
|---------|--------|----------|----------|------|
| `[模块A]` | `[AggregateRoot1]` | `id, name, status` | [实体/值对象] | [说明] |
| `[模块A]` | `[AggregateRoot2]` | `id, ...` | [实体/值对象] | [说明] |
| `[模块B]` | `[AggregateRoot3]` | `id, ...` | [实体/值对象] | [说明] |

### 2.2 聚合根边界

#### [聚合根1]

```
┌─────────────────────────────────────────────────┐
│  [AggregateRoot1]                               │
│  ┌─────────────────────────────────────────┐   │
│  │  根实体 [AggregateRoot1]                │   │
│  │  - id: [AggregateRoot1Id]              │   │
│  │  - [核心字段]                           │   │
│  └─────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────┐   │
│  │  实体 [Entity1] (1:N)                  │   │
│  │  - id: [Entity1Id]                     │   │
│  │  - [字段列表]                           │   │
│  └─────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────┐   │
│  │  值对象 [ValueObject1] (1:1)            │   │
│  │  - [不可变字段]                         │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**不变量（Invariants）**：
- [不变量1]：[说明]
- [不变量2]：[说明]

**边界规则**：
- 外部只能通过聚合根 ID 访问
- 聚合根内部实体不能被外部直接修改
- 所有修改通过聚合根方法进行

#### [聚合根2]

[同上结构]

### 2.3 聚合根生命周期

| 聚合根 | 创建条件 | 状态转换 | 销毁条件 |
|--------|----------|----------|----------|
| `[AR1]` | [条件] | [状态图] | [软删除/硬删除] |
| `[AR2]` | [条件] | [状态图] | [软删除/硬删除] |

---

## 3. 实体关系图 `[必填]`

### 3.1 ER 图

```mermaid
erDiagram
    %% 实体定义
    [Entity1] {
        uuid id PK
        string name
        timestamp created_at
    }

    [Entity2] {
        uuid id PK
        uuid entity1_id FK
        string description
    }

    [Entity3] {
        uuid id PK
        string type
    }

    %% 关系定义
    [Entity1] ||--o{ [Entity2] : "关系描述"
    [Entity2] }|--|{ [Entity3] : "关系描述"
    [Entity1] ||--o{ [Entity3] : "关系描述"
```

### 3.2 关系说明

| 关系 | 类型 | 基数 | 级联行为 | 说明 |
|------|------|------|----------|------|
| `[Entity1] → [Entity2]` | 一对多 | 1:N | CASCADE | [说明] |
| `[Entity2] ↔ [Entity3]` | 多对多 | N:M | SET NULL | [说明] |
| `[Entity1] → [Entity3]` | 一对一 | 1:1 | RESTRICT | [说明] |

**关系基数符号说明**：
- `||--||` : 一对一 (1:1)
- `||--o{` : 一对多 (1:N)
- `}|--|{` : 多对多 (N:M)

---

## 4. 表结构设计 `[必填]`

### 4.1 [模块A] 表结构

#### 4.1.1 [table_name] ([中文描述])

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `id` | `[UUID/BIGINT]` | PK, NOT NULL | - | 主键 |
| `[field1]` | `[类型]` | `[约束]` | `[默认值]` | [说明] |
| `[field2]` | `[类型]` | `[约束]` | `[默认值]` | [说明] |
| `created_at` | `TIMESTAMP` | NOT NULL | NOW() | 创建时间 |
| `updated_at` | `TIMESTAMP` | NOT NULL | NOW() | 更新时间 |
| `deleted_at` | `TIMESTAMP` | NULL | NULL | 软删除时间 |

**索引**：
```sql
-- 主键索引
PRIMARY KEY (id)

-- 唯一索引
CREATE UNIQUE INDEX uniq_[table]_[field] ON [table_name]([field]);

-- 普通索引
CREATE INDEX idx_[table]_[field] ON [table_name]([field]);

-- 复合索引
CREATE INDEX idx_[table]_[field1]_[field2] ON [table_name]([field1], [field2]);
```

**约束**：
```sql
-- 外键约束
ALTER TABLE [table_name]
ADD CONSTRAINT fk_[table]_[ref_table]
FOREIGN KEY ([fk_field]) REFERENCES [ref_table](id)
ON DELETE [CASCADE/SET NULL/RESTRICT]
ON UPDATE CASCADE;

-- CHECK 约束
ALTER TABLE [table_name]
ADD CONSTRAINT chk_[table]_[condition]
CHECK ([condition]);
```

#### 4.1.2 [table_name2] ([中文描述])

[同上结构]

### 4.2 [模块B] 表结构

#### 4.2.1 [table_name] ([中文描述])

[同上结构]

---

## 5. 索引设计 `[标准+]`

### 5.1 索引清单

| 表名 | 索引名 | 索引字段 | 索引类型 | 唯一 | 说明 |
|------|--------|----------|----------|------|------|
| `[table1]` | `idx_[table1]_[field]` | `[field]` | BTREE | 否 | [查询场景] |
| `[table1]` | `uniq_[table1]_[field]` | `[field]` | BTREE | 是 | [唯一约束] |
| `[table2]` | `idx_[table2]_[f1]_[f2]` | `[f1], [f2]` | BTREE | 否 | [复合查询] |
| `[table3]` | `idx_[table3]_[field]` | `[field]` | HASH | 否 | [等值查询] |

### 5.2 索引策略

#### 选择原则

- **高频查询字段**：WHERE 条件、JOIN 字段、ORDER BY 字段
- **选择性高的字段**：唯一值多的字段优先建索引
- **复合索引顺序**：选择性高的字段在前
- **避免过度索引**：每个表不超过 [5-10] 个索引

#### 索引类型选择

| 索引类型 | 适用场景 | 示例 |
|----------|----------|------|
| **B-Tree** | 范围查询、排序 | `WHERE created_at > ?` |
| **Hash** | 等值查询 | `WHERE status = ?` |
| **Full-Text** | 全文搜索 | `WHERE content LIKE ?` |
| **GiST** | 地理位置、范围 | `WHERE location && ?` |

#### 待优化索引

[根据查询分析结果，列出需要添加/删除/调整的索引]

---

## 6. 数据一致性 `[标准+]`

### 6.1 并发控制

#### 场景分析

| 场景 | 并发风险 | 控制方式 | 说明 |
|------|----------|----------|------|
| `[场景1]` | `[风险描述]` | `[乐观锁/悲观锁/分布式锁]` | [说明] |
| `[场景2]` | `[风险描述]` | `[乐观锁/悲观锁/分布式锁]` | [说明] |

#### 实现方式

**乐观锁（推荐）**：
```sql
ALTER TABLE [table_name]
ADD COLUMN version BIGINT NOT NULL DEFAULT 0;

-- 更新时检查版本
UPDATE [table_name]
SET [fields] = [values], version = version + 1
WHERE id = ? AND version = ?;
```

**悲观锁**：
```sql
-- SELECT FOR UPDATE
BEGIN;
SELECT * FROM [table_name] WHERE id = ? FOR UPDATE;
-- 业务处理
COMMIT;
```

**分布式锁**：
- 使用 [Redis] 实现
- 锁粒度：[资源级别]
- 超时时间：[X 秒]

### 6.2 事务边界

| 业务操作 | 涉及表 | 事务级别 | 说明 |
|---------|--------|----------|------|
| `[操作1]` | `[表列表]` | READ_COMMITTED | [说明] |
| `[操作2]` | `[表列表]` | SERIALIZABLE | [说明] |
| `[操作3]` | `[表列表]` | REPEATABLE_READ | [说明] |

**事务级别说明**：
- **READ_UNCOMMITTED**：可能读未提交数据（不推荐）
- **READ_COMMITTED**：避免脏读（默认）
- **REPEATABLE_READ**：避免不可重复读
- **SERIALIZABLE**：完全串行化（最高隔离）

### 6.3 约束设计

#### 数据库约束

| 约束类型 | 说明 | 示例 |
|----------|------|------|
| **NOT NULL** | 字段不能为空 | `name VARCHAR NOT NULL` |
| **UNIQUE** | 字段值唯一 | `email VARCHAR UNIQUE` |
| **CHECK** | 自定义验证 | `CHECK (age >= 18)` |
| **FOREIGN KEY** | 外键引用 | `REFERENCES user(id)` |

#### 应用层约束

- [约束1]：[说明]
- [约束2]：[说明]

#### 触发器

```sql
-- [触发器示例]
CREATE TRIGGER [trigger_name]
BEFORE INSERT ON [table_name]
FOR EACH ROW
BEGIN
    -- 触发逻辑
END;
```

---

## 7. 迁移规划 `[完整]`

### 7.1 迁移脚本

| 版本 | 变更内容 | 向前迁移 | 向后回滚 |
|------|----------|----------|----------|
| `001_initial` | 创建初始表结构 | `upgrade()` | `downgrade()` |
| `002_add_indexes` | 添加索引 | `upgrade()` | `downgrade()` |
| `003_add_column` | 新增字段 | `upgrade()` | `downgrade()` |

#### 迁移脚本示例

```python
# Alembic 迁移示例
def upgrade():
    op.create_table(
        'table_name',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_table_name_field', 'table_name', ['field'])

def downgrade():
    op.drop_index('idx_table_name_field', 'table_name')
    op.drop_table('table_name')
```

### 7.2 数据迁移策略

#### 迁移场景

| 场景 | 迁移方式 | 停机时间 | 回滚方案 |
|------|----------|----------|----------|
| `[场景1]` | [在线迁移/停机迁移] | [X 分钟] | [回滚步骤] |
| `[场景2]` | [在线迁移/停机迁移] | [X 分钟] | [回滚步骤] |

#### 数据一致性校验

```sql
-- 迁移前后数据量校验
SELECT COUNT(*) FROM source_table;
SELECT COUNT(*) FROM target_table;

-- 数据内容校验
SELECT COUNT(*) FROM source_table
WHERE id NOT IN (SELECT id FROM target_table);
```

### 7.3 演进规则

#### 兼容性原则

| 操作 | 向前兼容策略 | 示例 |
|------|--------------|------|
| **新增字段** | 添加可空字段 | `ALTER TABLE ADD COLUMN new_field VARCHAR NULL` |
| **修改字段** | 两步走（新增→迁移→删除旧） | 见下方详细流程 |
| **删除字段** | 先标记 deprecated | `ALTER COLUMN deleted_field SET DEFAULT 'deprecated'` |
| **重命名** | 新增字段 + 视图兼容 | `CREATE VIEW AS SELECT old AS new` |

#### 字段类型变更流程

```
1. 添加新字段（可空）
   ALTER TABLE t ADD COLUMN new_field NEW_TYPE NULL;

2. 数据迁移（分批）
   UPDATE t SET new_field = CAST(old_field AS NEW_TYPE) WHERE id BETWEEN ? AND ?;

3. 添加非空约束
   ALTER TABLE t ALTER COLUMN new_field SET NOT NULL;

4. 删除旧字段（下个版本）
   ALTER TABLE t DROP COLUMN old_field;
```

---

## 8. 附录 `[必填]`

### 8.1 术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| `[术语1]` | `[English Term]` | [说明] |
| `[术语2]` | `[English Term]` | [说明] |

### 8.2 变更日志

| 版本 | 日期 | 变更内容 | 责任人 |
|------|------|----------|--------|
| v1.0 | [YYYY-MM-DD] | 初始版本 | [AI + User] |

---

**文档结束**
