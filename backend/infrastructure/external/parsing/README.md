# infrastructure/external/parsing 文档解析集成

实现 `application/ports/document_parser.py` 的 `DocumentParserPort`：任意格式 → 规范化 Markdown。

## 文件索引

| 文件 | 职责 |
|------|------|
| `__init__.py` | `create_parser()` / `get_parser()` 工厂：按 `DOCUMENT__PARSER` 实例化，懒导入 provider |
| `providers/markitdown.py` | 默认 provider：本地解析 Office/HTML/txt/数字原生 PDF（依赖 `documents` extra） |
| `providers/textin.py` | 可选 provider：TextIn 公有云 API，覆盖扫描件/复杂版式 PDF，按页计费 |

## 约定

- **二选一，不混用**：`DOCUMENT__PARSER=markitdown`（默认）或 `textin`，无静默降级
- markitdown 对扫描件抛 `document.parse.empty_content`（显式拒绝，提示切换 textin）
- TextIn 凭证（`DOCUMENT__TEXTIN_APP_ID` / `DOCUMENT__TEXTIN_SECRET_CODE`）为长期有效凭证，
  缺失时在 settings 加载阶段 fail-fast
- 解析失败统一抛 `DocumentParserError(code, message)`，code 落库到 `documents.error_code`
- 模式对齐 `external/storage`：工厂 + 懒导入，可选依赖只在被选中时才需要安装
