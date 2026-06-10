# 2026-06-10 文档解析模块（Document 聚合 + ParserPort）

## §0 Triage

| # | 问题 | 答案 |
|---|------|------|
| 1 | 只服务一个明确的用户目标？ | 是（上传的文件 → AI 可消费的 Markdown） |
| 2 | 只影响一个业务模块？ | 是（新增 document 模块，file_asset 只读引用） |
| 3 | 不改数据库 schema / migration？ | **否**（新增 documents 表 + 迁移 0002） |
| 4 | 不改公共 API 契约？ | **否**（新增 /api/v1/documents 端点） |
| 5 | 不涉及 domain 规则变化？ | **否**（新增 Document 聚合与状态机） |
| 6 | 不涉及外部系统？ | **否**（TextIn HTTP API，可选） |
| 7 | 不涉及权限/安全/幂等/复杂状态流转？ | 是（仅复用 get_current_user 闸门；状态机简单） |
| 8 | 只改少量文件且不超过 2 层？ | 否（四层全触达） |

→ 4 个"否"，但变更是模板级标准聚合扩展（完全复制 file_asset/conversation 既有模式），按 **Flow B** 执行（第 1+2 层）。

**约束清单**
- 硬约束（用户明确要求）：
  - 解析器二选一，环境变量配置（`DOCUMENT__PARSER`），默认 `markitdown`
  - 不引入 GB 级依赖（排除 Docling/MinerU 本地），不引入会过期的 token（排除 MinerU Web API）
  - TextIn 作为可选解析器（公有云允许）
- 隐含约束（来自现有代码/架构）：
  - DDD 分层、UoW 注册表 + service-local Protocol、BaseEntity 继承、Response 信封、business code、i18n message_key
  - markitdown 进 optional-dependencies（kit extras 拆分原则）
  - 外部调用不进 DB 事务（transaction-side-effects）
  - 解析失败不静默降级到另一个解析器（用户确认：二选一不混用）
- 需确认：无（对话中已全部确认）

## 第 1 层

**目标**：上传到对象存储的文件（经 file_asset），可创建为 Document 并异步解析为规范化 Markdown，状态机驱动（pending → parsing → ready / failed），解析器按环境变量二选一。

**范围**：
- `domain/document/`：Document 聚合（实体 + 状态机 + 仓储接口 + 异常）
- `application/ports/document_parser.py`：DocumentParserPort + ParsedDocument + ParserError
- `application/ports/storage.py`：新增 `download(key) -> bytes`（适配器已具备底层能力）
- `application/services/document_service.py`：建档/异步解析/查询/重解析编排
- `infrastructure/`：ORM model、repository、UoW 注册、`external/parsing/`（markitdown + textin 两个 provider + 工厂）
- `api/routes/documents.py` + dependencies/main.py 接线
- `core/config.py`：DocumentSettings（parser 二选一校验，textin 凭证 fail-fast）
- Alembic 迁移 0002；pyproject `documents` extra
- 不在范围：分块/嵌入/索引（下游 RAG 关注点）、Celery 接入（默认 BackgroundTasks，留 hook）、扫描件 OCR、ownership 细粒度权限（与 files 模块同等留白）

**影响范围**：纯新增；唯一触碰的既有契约是 StoragePort 增加 download 方法（向后兼容的扩展）。

**风险**：
- markitdown 是可选依赖，未安装时首个解析请求报 RuntimeError（带安装指引）——与 s3/oss 懒加载同模式
- BackgroundTasks 进程内执行，进程重启丢任务 → 状态停在 parsing；提供 reparse 端点兜底
- TextIn 是外部系统：超时/错误码映射为 failed + error_code，不重试（按页计费，重试需幂等判断，留给下游）

**验收标准**：
1. `DOCUMENT__PARSER` 缺省时用 markitdown；设为 `textin` 但缺凭证时启动即失败
2. POST /api/v1/documents {file_asset_id} → pending/parsing；解析完成后 GET 返回 ready + content 可取 Markdown
3. markitdown 解析 PDF 得到近空文本 → failed + `document.parse.empty_content`（扫描件显式拒绝）
4. TextIn API 错误 → failed + TextIn 错误码，无静默降级
5. pytest 覆盖实体状态机、服务编排（fake parser/storage/UoW）、textin 错误映射

## 第 2 层

**术语**：Document（语义层聚合，引用 FileAsset）、ParserPort（解析端口）、canonical Markdown（统一中间表示）。

**现状**：file_asset 聚合只管字节生命周期；无任何解析能力；StoragePort 无 download。

**方案概述**：标准 DDD 纵切。解析流程三段式（事务外做 I/O）：
```
uow1: load doc + guard + mark parsing + commit
     ↓（事务外）storage.download → parser.parse
uow2: mark ready(markdown) / failed(code,msg) + commit
```
路由用 FastAPI BackgroundTasks 调度 `process_document`；服务方法本身可被 Celery task 直接复用。

**核心流程**：
```
POST /documents → create(pending) → BackgroundTasks(process)
process: parsing → download → parse → ready/failed
GET /documents/{id} → 状态轮询
GET /documents/{id}/content → ready 时返回 markdown，否则 DocumentNotReady
POST /documents/{id}/reparse → failed/ready 可重跑（parsing 中拒绝）
```

## §11 执行步骤

1. domain/document（实体+接口+异常）+ business codes + 单测
2. infrastructure：model + repository + UoW 注册 + 迁移 0002
3. ports（document_parser + storage.download）+ config + parsing providers + pyproject extra
4. application service + DTO + 单测
5. API 路由 + 接线 + README/头注释 + data/api docs
6. 验证（pytest + flake8）+ review skill + 修 blocking
