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
| DELETE | `/api/v1/files/{id}` | 软删除；`data = { id, deleted: true }` |

## storage 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/storage/presign-upload` | 客户端直传预签名（幂等，见 conventions.md）；创建 pending 资产并写 owner |
| POST | `/api/v1/storage/complete` | 直传完成确认（按 `id` 或 `key`）；仅资产 owner 可确认；见下方确认规则 |
| POST | `/api/v1/storage/upload` | 服务端中转上传；落库即 active 并写 owner |

## 直传预签名（`/storage/presign-upload`）

- presign 时声明的 `size_bytes`（> 0）随签名下传：S3 PUT 把 `Content-Length` 纳入 SigV4 签名头
  （客户端实际上传的字节数必须与声明一致，否则 S3 拒绝该 PUT）；S3 POST 在 policy 里加
  `content-length-range [size, size]`。`size_bytes=0` 视为未声明，不绑定大小。
- 同一 `Idempotency-Key` 重放：只要资产仍是 `pending`，就按**库里资产**的 key / content_type /
  声明大小重新签发上传链接（响应 `file` 仍是首次的缓存摘要）；资产已确认（active）或已删除 →
  `FILE_UPLOAD_CLOSED (20006)` / HTTP 409（`message_key=file.upload_closed`），不签发任何写链接。
- 已知残余限制：确认前已签发的链接在 `expires_in`（≤ 3600s）内仍然有效。S3 下它被绑定为声明的
  大小与类型，确认后只能被同尺寸同类型的内容覆盖；OSS / local 的签名 PUT 无法绑定大小，
  确认后的覆盖只能靠更短的 `expires_in` 缓解（更强方案是带 `content-length-range` 的 POST policy）。

## 直传确认（`/storage/complete`）

- 确认时以存储 HEAD 回来的**真实对象**复核 presign 策略：实际大小超过 `storage.presign_max_size`、
  与 presign 时声明的 `size_bytes` 不一致（声明为 0 视为未声明），或实际类型不在
  `storage.presign_content_types` 内 → 尽力删除存储对象、资产软删，返回
  `FileTooLarge` / `validation.failed` / `UnsupportedMimeType`（`PARAM_VALIDATION_ERROR (10003)` / 422）。
- 对象尚未上传到存储 → `FILE_NOT_UPLOADED (20005)` / HTTP 409（`message_key=file.not_uploaded`），
  资产保持 pending，客户端上传完成后可重试。
- 激活写入守卫 `deleted_at IS NULL`：确认期间资产被并发删除 → 404，不会被复活。
