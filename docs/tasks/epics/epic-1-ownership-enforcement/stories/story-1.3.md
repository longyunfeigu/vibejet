# Story 1.3: files + storage 端点归属闭环

**As a** 登录用户
**I want** 文件列表/详情/签名 URL/删除/上传确认只作用于我自己的文件
**So that** 他人无法枚举、下载或删除我的文件

**依赖**: 无

## 范围

- `application/services/file_asset_service.py`：route-facing 方法增加必填 `owner_id` 归属断言——`get_asset_raw`、`get_asset_by_key_raw`（storage/complete 用）、`soft_delete`、`confirm_direct_upload`；`list_assets` 已有 owner_id 参数，不改签名。内部方法（purge/mark_active/后台清理）不加。
- `api/routes/files.py`：5 个端点改为读取 `current_user`，list 传 `owner_id=current_user.id`（替换 `owner_id = None`），详情/预览/下载/删除断言归属，失败抛 `FileAssetNotFoundException`（404）
- `api/routes/storage.py`：`/storage/complete` 断言待确认资产归属当前用户（presign/upload 已写 owner，不动）

#### 验收标准

**Happy Path**
- [ ] 文件列表只含当前用户的文件（signed 与非 signed 均是） `验证: pytest tests/test_file_ownership.py -k list_scoped → passed`
- [ ] owner 可获取详情、生成预览/下载 URL、软删除 `验证: pytest tests/test_file_ownership.py -k owner_full_access → passed`

**Edge Cases**
- [ ] owner_id 为 NULL 的遗留资产对任何用户不可见/404 `验证: pytest tests/test_file_ownership.py -k legacy_null → passed`

**Error Paths**
- [ ] 非 owner 访问详情/预览 URL/下载 URL/删除 → 404 `验证: pytest tests/test_file_ownership.py -k non_owner_404 → passed`
- [ ] 非 owner 调用 /storage/complete 确认他人 pending 资产 → 404 且资产状态不变 `验证: pytest tests/test_file_ownership.py -k complete_non_owner → passed`

**Integration**
- [ ] presign → complete 全链路：A 预签名、A 确认成功；B 确认失败 `验证: pytest tests/test_file_ownership.py -k presign_complete_flow → passed`
