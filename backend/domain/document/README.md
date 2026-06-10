# domain/document 文档聚合

语义层聚合：把上传的文件（`file_asset`，字节层事实）解析为 AI 可消费的规范化 Markdown。

## 文件索引

| 文件 | 职责 |
|------|------|
| `entity.py` | `Document` 聚合根：pending → parsing → ready / failed 状态机，持有解析产物 `content_md` |
| `repository.py` | `DocumentRepository` ABC 仓储接口 |
| `exceptions.py` | `DocumentNotFound` / `DocumentNotReady` / `DocumentAlreadyProcessing` |
| `__init__.py` | 包导出 |

## 设计要点

- `Document` 通过 `file_asset_id` 逻辑引用文件资产，不持有字节；重解析不触碰文件记录
- `parsing` 状态下禁止再次进入 parsing 或重置（`DocumentAlreadyProcessingException`）
- `ready`/`failed` 可经 `reset_for_reparse()` 回到 `pending`（清空旧产物与错误）
- 解析器选择、下载、HTTP 都不在本层 —— 领域层只表达状态与不变量
