# Performance Checklist (Python / FastAPI)

当改动涉及数据库操作、API 端点、列表查询、文件处理、前端渲染时，在 Pass 2 中额外检查以下项。

## B.1 数据库

- [ ] 无 N+1 查询模式（使用 `selectinload` / `joinedload` / 批量查询）
- [ ] 查询有合适的索引（WHERE / ORDER BY 的列）
- [ ] 列表端点有分页，不返回全表（禁止无 LIMIT 的 `SELECT *`）
- [ ] 连接池已配置（`pool_size`、`max_overflow`）
- [ ] 慢查询有日志或监控
- [ ] 批量写入使用 `bulk_insert_mappings` / `bulk_update_mappings`，不在循环中逐条写

## B.2 API 端点

- [ ] 响应时间 p95 < 200ms（复杂查询 < 500ms）
- [ ] 请求处理器中无同步阻塞计算（CPU 密集任务走 Celery / 线程池）
- [ ] 批量操作代替循环单条调用
- [ ] 响应压缩已启用（gzip / brotli）
- [ ] 适当的缓存策略（内存缓存 / Redis / HTTP Cache-Control）
- [ ] 大文件流式返回（`StreamingResponse`），不一次性加载到内存

## B.3 异步与并发

- [ ] 外部 HTTP 调用使用 `httpx.AsyncClient`，不使用同步 `requests`
- [ ] 多个独立外部调用使用 `asyncio.gather` 并行，不串行 await
- [ ] 有并发上限（`asyncio.Semaphore`），防止资源耗尽
- [ ] WebSocket / SSE 有背压控制和连接上限
- [ ] 长时间运行的任务有超时设置

## B.4 内存与资源

- [ ] 大数据集使用生成器 / 流式处理，不一次性加载
- [ ] 文件处理有大小限制，防止内存溢出
- [ ] 临时文件及时清理
- [ ] 无明显内存泄漏（未关闭的连接、未清理的缓存、无限增长的列表）

## B.5 前端（如涉及）

- [ ] 初始 bundle 大小 < 200KB gzipped
- [ ] 路由级别的代码分割（`React.lazy` + `Suspense`）
- [ ] 图片使用 WebP 格式 + `loading="lazy"`（非首屏图片）
- [ ] 长列表使用虚拟化（`react-window` / `react-virtuoso`）
- [ ] 无不必要的全页面重渲染

## B.6 常见反模式速查

| 反模式 | 影响 | 修复方式 |
|--------|------|---------|
| N+1 查询 | DB 负载线性增长 | 使用 `selectinload` / JOIN / 批量加载 |
| 无限查询 | 内存耗尽、超时 | 始终分页，加 LIMIT |
| 缺少索引 | 数据增长后读取变慢 | 给 WHERE / ORDER BY 列加索引 |
| 同步阻塞 | 请求线程被阻塞 | 使用 async 或 offload 到线程池 |
| 串行外部调用 | 延迟叠加 | `asyncio.gather` 并行调用 |
| 全量加载到内存 | OOM 风险 | 流式处理 / 分批加载 |
| 无缓存 | 重复计算 / 重复查询 | 内存缓存 / Redis / HTTP 缓存 |
| 无背压 | 资源耗尽 | Semaphore / 连接上限 / 队列 |
