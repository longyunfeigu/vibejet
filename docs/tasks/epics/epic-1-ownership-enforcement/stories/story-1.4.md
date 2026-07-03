# Story 1.4: documents 端点归属闭环 + catalog 同步

**As a** 登录用户
**I want** 文档列表/详情/内容/重解析/删除只作用于我自己的文档
**So that** 他人无法读取或操作我的文档

**依赖**: 无

## 范围

- `application/services/document_service.py`：route-facing 方法增加必填 `owner_id` 归属断言——`get_document`、`get_document_content`、`reset_for_reparse`、`soft_delete`；`list_documents` 已有 owner_id 参数不改签名；`create_document` 已写 owner 不动；`process_document`（后台 worker）不加。
- `api/routes/documents.py`：list 传 `owner_id=current_user.id`（替换 None），详情/内容/重解析/删除断言归属，失败抛 `DocumentNotFoundException`（404，经 Story 1.1 的映射修正）
- Catalog 同步：`docs/project/api/conventions.md` 鉴权段更新（ownership 已强制 + 404 语义）；`docs/project/api/documents.md` 增补 owner 过滤与 404 行为；新建 `docs/project/api/conversations.md`、`docs/project/api/files.md` 端点契约；新建 `docs/project/data/conversation.md`（owner_id schema delta）

#### 验收标准

**Happy Path**
- [ ] 文档列表只含当前用户的文档 `验证: pytest tests/test_document_ownership.py -k list_scoped → passed`
- [ ] owner 可获取详情/内容、触发重解析、软删除 `验证: pytest tests/test_document_ownership.py -k owner_full_access → passed`

**Edge Cases**
- [ ] owner_id 为 NULL 的遗留文档对任何用户 404 `验证: pytest tests/test_document_ownership.py -k legacy_null → passed`

**Error Paths**
- [ ] 非 owner 访问详情/内容/重解析/删除 → 404 `验证: pytest tests/test_document_ownership.py -k non_owner_404 → passed`

**Integration**
- [ ] 后台解析 worker（process_document）不受归属参数影响仍可处理任意文档 `验证: pytest tests/test_document_service.py → passed（既有用例回归）`
