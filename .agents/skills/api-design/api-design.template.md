# API 设计文档模板

> **版本**: v1.0
> **更新日期**: YYYY-MM-DD
> **文档状态**: [草稿/评审中/已发布]
> **作者**: [作者姓名]
> **架构文档来源**: [docs/architecture.md 或"无"]
> **PRD 来源**: [docs/prd.md 或"无"]

---

## 模板使用说明

<!-- 本注释块在生成实际文档时删除 -->

### 章节必填说明

| 标记 | 含义 | 模式要求 |
|------|------|----------|
| `[必填]` | 所有模式必须填写 | 快速/标准/完整 |
| `[标准+]` | 标准和完整模式填写 | 标准/完整 |
| `[完整]` | 仅完整模式填写 | 完整 |

### 填写原则

1. **删除未使用的章节**：根据选择的模式，删除不需要的章节
2. **删除模板注释**：所有 `<!-- -->` 注释在最终文档中删除
3. **替换占位符**：将 `[占位符]` 替换为实际内容
4. **保留结构**：保持标题层级和表格格式

---

## 目录

1. [API 概述](#1-api-概述) `[必填]`
2. [资源定义](#2-资源定义) `[必填]`
3. [通用规范](#3-通用规范) `[标准+]`
4. [端点详情](#4-端点详情) `[必填]`
5. [错误处理](#5-错误处理) `[标准+]`
6. [认证与授权](#6-认证与授权) `[标准+]`
7. [版本管理](#7-版本管理) `[完整]`
8. [Schema 定义](#8-schema-定义) `[必填]`
9. [附录](#9-附录) `[必填]`

---

# [项目名称] - API 设计文档

---

## 1. API 概述 `[必填]`

### 1.1 设计原则

<!-- 至少填写 3 条原则，根据项目实际需求调整 -->

| 原则 | 说明 | 实践方式 |
|------|------|----------|
| **RESTful 风格** | 资源导向，语义化 HTTP 方法 | 名词复数、正确使用 GET/POST/PUT/DELETE |
| **一致性** | 命名、格式、错误处理统一 | 遵循本文档规范 |
| **安全性** | 认证授权、数据保护 | JWT + RBAC，HTTPS 强制 |
| **可扩展** | 版本管理、向后兼容 | URL 版本号，字段仅增不删 |
| **可观测** | 请求追踪、错误定位 | request_id 贯穿全链路 |

### 1.2 基础信息

| 项目 | 值 | 说明 |
|------|-----|------|
| **Base URL** | `https://api.example.com/api/v1` | 生产环境 |
| **Base URL (Dev)** | `http://localhost:8000/api/v1` | 开发环境 |
| **协议** | HTTPS (生产) / HTTP (开发) | 生产强制 TLS 1.2+ |
| **数据格式** | JSON (application/json) | UTF-8 编码 |
| **时间格式** | ISO 8601 (UTC) | `2024-01-01T00:00:00Z` |
| **字符编码** | UTF-8 | 所有文本字段 |

### 1.3 统一响应格式

#### 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    // 业务数据
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### 分页响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 100,
      "total_pages": 5
    }
  },
  "request_id": "...",
  "timestamp": "..."
}
```

#### 错误响应

```json
{
  "code": 400001,
  "message": "参数校验失败",
  "error": {
    "field": "email",
    "detail": "邮箱格式不正确"
  },
  "request_id": "...",
  "timestamp": "..."
}
```

---

## 2. 资源定义 `[必填]`

### 2.1 资源清单

| 资源名称 | URL 路径 | 所属模块 | 说明 | 核心操作 |
|----------|----------|----------|------|----------|
| [资源1] | `/[资源1]` | [模块A] | [说明] | CRUD |
| [资源2] | `/[资源2]` | [模块A] | [说明] | CRUD |
| [嵌套资源] | `/[父资源]/{id}/[子资源]` | [模块B] | [说明] | CRUD |

### 2.2 资源关系图

```
┌─────────────┐
│   [资源A]   │
└──────┬──────┘
       │ 1:N
       ▼
┌─────────────┐     N:M     ┌─────────────┐
│   [资源B]   │────────────►│   [资源C]   │
└─────────────┘             └─────────────┘
```

### 2.3 命名规范

| 规范项 | 规则 | 正确示例 | 错误示例 |
|--------|------|----------|----------|
| 资源名 | 名词复数，kebab-case | `/knowledge-bases` | `/knowledgeBase`, `/getUsers` |
| 路径参数 | snake_case | `{user_id}` | `{userId}`, `{user-id}` |
| 查询参数 | snake_case | `?sort_by=created_at` | `?sortBy=createdAt` |
| 请求体字段 | snake_case | `"user_name"` | `"userName"` |

---

## 3. 通用规范 `[标准+]`

### 3.1 分页

#### 偏移分页（默认）

```
GET /resources?page=1&size=20
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | integer | 否 | 1 | 页码，从 1 开始 |
| `size` | integer | 否 | 20 | 每页数量，最大 100 |

响应示例：

```json
{
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 156,
      "total_pages": 8
    }
  }
}
```

#### 游标分页（大数据集推荐）

```
GET /resources?cursor=xxx&size=20
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cursor` | string | 否 | 上次返回的游标值，首次请求不传 |
| `size` | integer | 否 | 每页数量 |

响应示例：

```json
{
  "data": {
    "items": [...],
    "pagination": {
      "next_cursor": "eyJpZCI6MTAwfQ==",
      "has_more": true
    }
  }
}
```

### 3.2 排序

```
GET /resources?sort_by=created_at&sort_order=desc
```

| 参数 | 类型 | 默认值 | 可选值 |
|------|------|--------|--------|
| `sort_by` | string | `created_at` | 资源支持的排序字段 |
| `sort_order` | string | `desc` | `asc`, `desc` |

### 3.3 筛选

```
GET /resources?status=active&created_after=2024-01-01T00:00:00Z
```

| 筛选模式 | 格式 | 示例 |
|----------|------|------|
| 精确匹配 | `field=value` | `status=active` |
| 多值匹配 | `field=v1,v2` | `status=active,pending` |
| 范围查询 | `field_after`, `field_before` | `created_after=2024-01-01` |
| 模糊搜索 | `q=keyword` | `q=john` |

### 3.4 字段选择 `[完整]`

```
GET /resources?fields=id,name,status
```

- 仅返回指定字段，减少响应体积
- 不指定时返回所有字段

### 3.5 关联展开 `[完整]`

```
GET /resources/{id}?expand=author,comments
```

- 展开关联资源，减少请求次数
- 支持多级展开：`expand=author.profile`

---

## 4. 端点详情 `[必填]`

### 4.1 [模块名称] API

<!-- 按模块组织端点，每个模块重复此结构 -->

#### 4.1.1 [获取资源列表]

- **端点**: `GET /[资源]`
- **描述**: [功能描述]
- **认证**: [是/否]
- **权限**: [角色列表]

**请求参数**

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| `page` | query | integer | 否 | 页码 |
| `size` | query | integer | 否 | 每页数量 |
| `[筛选字段]` | query | string | 否 | [说明] |

**请求示例**

```bash
curl -X GET "https://api.example.com/api/v1/[资源]?page=1&size=20" \
  -H "Authorization: Bearer <token>"
```

**响应示例**

成功 (200):
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "uuid",
        "name": "示例",
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 1,
      "total_pages": 1
    }
  }
}
```

---

#### 4.1.2 [获取资源详情]

- **端点**: `GET /[资源]/{id}`
- **描述**: [功能描述]
- **认证**: [是/否]
- **权限**: [角色列表]

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | string (UUID) | 资源唯一标识 |

**请求示例**

```bash
curl -X GET "https://api.example.com/api/v1/[资源]/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <token>"
```

**响应示例**

成功 (200):
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "示例",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

失败 (404):
```json
{
  "code": 404001,
  "message": "资源不存在",
  "error": {
    "resource": "[资源名]",
    "id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

#### 4.1.3 [创建资源]

- **端点**: `POST /[资源]`
- **描述**: [功能描述]
- **认证**: 是
- **权限**: [角色列表]

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 名称，1-100 字符 |
| `description` | string | 否 | 描述，最大 500 字符 |
| `[其他字段]` | [类型] | [是/否] | [说明] |

**请求示例**

```bash
curl -X POST "https://api.example.com/api/v1/[资源]" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "新资源",
    "description": "描述"
  }'
```

**响应示例**

成功 (201):
```json
{
  "code": 0,
  "message": "创建成功",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "新资源",
    "description": "描述",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

失败 (400):
```json
{
  "code": 400001,
  "message": "参数校验失败",
  "error": {
    "field": "name",
    "detail": "名称不能为空"
  }
}
```

失败 (409):
```json
{
  "code": 409001,
  "message": "资源已存在",
  "error": {
    "field": "name",
    "detail": "名称 '新资源' 已被使用"
  }
}
```

---

#### 4.1.4 [更新资源]

- **端点**: `PUT /[资源]/{id}` (全量更新) 或 `PATCH /[资源]/{id}` (部分更新)
- **描述**: [功能描述]
- **认证**: 是
- **权限**: [角色列表]

**请求体** (PATCH - 所有字段可选)

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 名称 |
| `description` | string | 描述 |

**请求示例**

```bash
curl -X PATCH "https://api.example.com/api/v1/[资源]/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "更新后的名称"
  }'
```

**响应示例**

成功 (200):
```json
{
  "code": 0,
  "message": "更新成功",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "更新后的名称",
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

---

#### 4.1.5 [删除资源]

- **端点**: `DELETE /[资源]/{id}`
- **描述**: [功能描述]
- **认证**: 是
- **权限**: [角色列表]

**请求示例**

```bash
curl -X DELETE "https://api.example.com/api/v1/[资源]/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <token>"
```

**响应示例**

成功 (200):
```json
{
  "code": 0,
  "message": "删除成功",
  "data": null
}
```

成功 (204): 无响应体

---

#### 4.1.6 [自定义操作] `[按需]`

- **端点**: `POST /[资源]/{id}/[动作]`
- **描述**: [功能描述]
- **认证**: 是
- **权限**: [角色列表]

**请求示例**

```bash
curl -X POST "https://api.example.com/api/v1/users/550e8400-e29b-41d4-a716-446655440000/activate" \
  -H "Authorization: Bearer <token>"
```

---

## 5. 错误处理 `[标准+]`

### 5.1 HTTP 状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 204 | No Content | 删除成功，无响应体 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证或 Token 无效 |
| 403 | Forbidden | 无权限访问 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突 |
| 422 | Unprocessable Entity | 业务规则校验失败 |
| 429 | Too Many Requests | 请求限流 |
| 500 | Internal Server Error | 服务器内部错误 |

### 5.2 业务错误码

<!-- 按模块组织错误码 -->

#### 通用错误 (400xxx)

| 错误码 | 说明 | HTTP 状态码 |
|--------|------|-------------|
| 400001 | 参数校验失败 | 400 |
| 400002 | 请求体格式错误 | 400 |
| 400003 | 必填参数缺失 | 400 |

#### 认证错误 (401xxx)

| 错误码 | 说明 | HTTP 状态码 |
|--------|------|-------------|
| 401001 | Token 无效 | 401 |
| 401002 | Token 已过期 | 401 |
| 401003 | 缺少认证信息 | 401 |

#### 授权错误 (403xxx)

| 错误码 | 说明 | HTTP 状态码 |
|--------|------|-------------|
| 403001 | 无操作权限 | 403 |
| 403002 | 资源访问被拒绝 | 403 |

#### [模块名] 错误 (4xxxx)

| 错误码 | 说明 | HTTP 状态码 |
|--------|------|-------------|
| [错误码] | [说明] | [状态码] |

### 5.3 错误响应格式

```json
{
  "code": 400001,
  "message": "参数校验失败",
  "error": {
    "field": "email",
    "detail": "邮箱格式不正确",
    "constraints": {
      "format": "email"
    }
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 5.4 多字段校验错误

```json
{
  "code": 400001,
  "message": "参数校验失败",
  "error": {
    "errors": [
      {
        "field": "email",
        "detail": "邮箱格式不正确"
      },
      {
        "field": "password",
        "detail": "密码长度至少 8 位"
      }
    ]
  }
}
```

---

## 6. 认证与授权 `[标准+]`

### 6.1 认证方案

| 项目 | 值 |
|------|-----|
| **认证方式** | JWT Bearer Token |
| **Token 类型** | access_token + refresh_token |
| **access_token 有效期** | [15分钟/1小时] |
| **refresh_token 有效期** | [7天/30天] |

#### 认证头格式

```
Authorization: Bearer <access_token>
```

#### 认证端点

| 端点 | 说明 |
|------|------|
| `POST /auth/login` | 登录，获取 Token |
| `POST /auth/refresh` | 刷新 access_token |
| `POST /auth/logout` | 登出，使 Token 失效 |

### 6.2 授权模型

| 项目 | 值 |
|------|-----|
| **授权模型** | RBAC (基于角色的访问控制) |
| **权限粒度** | 资源级 + 操作级 |

#### 角色定义

| 角色 | 代码 | 说明 |
|------|------|------|
| 超级管理员 | `superadmin` | 全部权限 |
| 管理员 | `admin` | 管理权限，不含系统配置 |
| 普通用户 | `user` | 基础功能 |
| 访客 | `guest` | 只读访问 |

#### 权限矩阵

| 端点 | guest | user | admin | superadmin |
|------|-------|------|-------|------------|
| `GET /users` | ❌ | ❌ | ✅ | ✅ |
| `GET /users/{id}` | ❌ | 仅自己 | ✅ | ✅ |
| `POST /users` | ❌ | ❌ | ✅ | ✅ |
| `PATCH /users/{id}` | ❌ | 仅自己 | ✅ | ✅ |
| `DELETE /users/{id}` | ❌ | ❌ | ❌ | ✅ |
| [其他端点] | ... | ... | ... | ... |

---

## 7. 版本管理 `[完整]`

### 7.1 版本策略

| 项目 | 值 |
|------|-----|
| **版本方案** | URL 路径版本 |
| **当前版本** | v1 |
| **版本格式** | `/api/v{major}/...` |

### 7.2 版本演进规则

| 变更类型 | 是否需要新版本 | 说明 |
|----------|----------------|------|
| 新增端点 | 否 | 向后兼容 |
| 新增响应字段 | 否 | 向后兼容 |
| 新增可选参数 | 否 | 向后兼容 |
| 删除端点 | 是 | 先 deprecated，下版本移除 |
| 删除响应字段 | 是 | 先 deprecated，下版本移除 |
| 修改字段类型 | 是 | 破坏性变更 |
| 修改业务逻辑 | 视情况 | 评估影响范围 |

### 7.3 废弃策略

```
废弃公告 ──▶ 并行运行 ──▶ 下线通知 ──▶ 正式下线
(T-6月)      (6个月)       (T-1月)       (T)
```

### 7.4 废弃标记

响应头：
```
Deprecation: true
Sunset: Sat, 01 Jul 2025 00:00:00 GMT
Link: <https://api.example.com/api/v2/users>; rel="successor-version"
```

---

## 8. Schema 定义 `[必填]`

### 8.1 通用类型

#### UUID

```typescript
type UUID = string; // 格式: "550e8400-e29b-41d4-a716-446655440000"
```

#### DateTime

```typescript
type DateTime = string; // ISO 8601 UTC: "2024-01-01T00:00:00Z"
```

#### Pagination

```typescript
interface Pagination {
  page: number;      // 当前页码
  size: number;      // 每页数量
  total: number;     // 总记录数
  total_pages: number; // 总页数
}
```

### 8.2 [资源名] Schema

#### [资源]DTO (响应)

```typescript
interface [资源]DTO {
  id: UUID;
  name: string;
  description: string | null;
  status: "[状态1]" | "[状态2]";
  created_at: DateTime;
  updated_at: DateTime;
}
```

#### Create[资源]Request (创建请求)

```typescript
interface Create[资源]Request {
  name: string;         // required, minLength: 1, maxLength: 100
  description?: string; // optional, maxLength: 500
}
```

#### Update[资源]Request (更新请求)

```typescript
interface Update[资源]Request {
  name?: string;        // optional
  description?: string; // optional
}
```

### 8.3 枚举定义

#### [资源]Status

| 值 | 说明 |
|-----|------|
| `[状态1]` | [说明] |
| `[状态2]` | [说明] |

---

## 9. 附录 `[必填]`

### A. 术语表

| 术语 | 说明 |
|------|------|
| [术语1] | [定义] |
| [术语2] | [定义] |

### B. 变更日志

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| 1.0.0 | YYYY-MM-DD | 初始版本 | [作者] |

### C. 设计决策记录 (ADR)

#### ADR-001: [决策标题]

- **状态**: [已采纳/已废弃/提议中]
- **决策**: [决策内容]
- **背景**: [为什么需要做这个决策]
- **理由**: [选择这个方案的原因]
- **影响**: [这个决策带来的影响]

### D. 参考资料

- [RESTful API 设计最佳实践](链接)
- [OpenAPI 3.0 规范](https://spec.openapis.org/oas/v3.0.3)
- [HTTP 状态码规范](https://httpstatuses.com)

---

*本文档最后更新：YYYY-MM-DD (v1.0)*
