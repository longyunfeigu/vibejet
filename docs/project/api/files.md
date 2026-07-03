# Files & Storage API

文件资产与对象存储模块公共接口。端点位于 `/api/v1/files` 与 `/api/v1/storage`，
要求 Bearer 认证，返回统一业务信封（见 [conventions.md](conventions.md)）。

**归属**：全部文件端点 owner-scoped——上传（presign / relay）写 `owner_id=当前用户`，
列表只返回自己的文件，详情/签名 URL/删除/上传确认越权 → `NOT_FOUND (20004)` / HTTP 404
（与不存在同响应）。

## files 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/files` | 分页列表（`page`/`size`/`kind`/`status`/`signed`/`expires_in`），仅当前用户 |
| GET | `/api/v1/files/{id}` | 详情；`signed=true` 时返回签名 URL |
| POST | `/api/v1/files/{id}/preview-url` | 生成预览链接（inline） |
| POST | `/api/v1/files/{id}/download-url` | 生成下载链接（attachment） |
| DELETE | `/api/v1/files/{id}` | 软删除 |

## storage 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/storage/presign-upload` | 客户端直传预签名（幂等，见 conventions.md）；创建 pending 资产并写 owner |
| POST | `/api/v1/storage/complete` | 直传完成确认（按 `id` 或 `key`）；仅资产 owner 可确认 |
| POST | `/api/v1/storage/upload` | 服务端中转上传；落库即 active 并写 owner |
