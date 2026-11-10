# 功能检查清单：可维护性重构（复杂度、重复度，Kafka 只保留 aiokafka）

> 由 `/feature-checklist` 产出。AUTO 项全部附有可以重跑的命令和结果；HUMAN 项由主会话判定，标「待审」。

Feature: 消除超复杂度函数，只保留 aiokafka 驱动并修好、补齐能力，修复文档解析超时
Type: 混合 T3 + T5 + T6
Generated: 2026-11-10
Design: [design.md](./design.md)
Release-Check: 豁免。有行为变化的部分（Kafka 驱动、消息投递语义、文档解析超时）都在可选扩展里，没有可以对着页面或接口做验收的入口，已经用单测和真实 broker 集成测试覆盖。commit 里带 `Release-Check: exempt` trailer。

---

## 检查清单与结果

### 复杂度与重复度

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 1 | AUTO | 整个后端没有超过复杂度上限的函数：`cd backend && uv run flake8 --select C901 .` | PASS | 输出为空；修改前有 12 个，最高 46 |
| 2 | AUTO | 重复度在门槛以下：jscpd，`--threshold 3` | PASS | 1.54%（修改前 2.36%） |
| 3 | AUTO | 12 个函数修改前后的复杂度 | PASS | `LoggingMiddleware.__call__` 14→2、`instrument_app` 11→6、gRPC 两个拦截器 11/12→6/7、`BaseAPIClient._request` 15→8、`RedisClient.lock` 13→4、`S3Provider.upload` 12→5、`MiddlewareStorage.upload` 12→9、`AiokafkaConsumer.start` 46→2；confluent 的 3 个随驱动一起删除 |

### 行为不变（特征测试）

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 4 | AUTO | HTTP/gRPC/tracing 的新测试，在原始代码上也全部通过 | PASS | 主会话复核：DEBUG=true、DEBUG=false、HEAD 的分离工作区（没有 .env）三种情况都是 131 passed |
| 5 | AUTO | 存储/缓存/HTTP 客户端的新测试，在原始代码上也全部通过 | PASS | 主会话复核：HEAD 的分离工作区 138 passed；当前代码 142 passed（含已有的 abort 测试） |
| 6 | AUTO | aiokafka 消费者的特征测试，在原始代码上也全部通过 | PASS | 消息 agent 报告：在 HEAD 版本的 consumer.py 上 60 passed。之后按设计改成断言修复后的行为 |
| 7 | HUMAN | 重构没有改变可观察行为 | PASS（待审） | 独立审查逐个对照了 8 个函数新旧版本的副作用顺序、异常、日志字段、请求头和计时，没有发现差异 |
| 8 | AUTO | 真实请求经过重构后的日志中间件 | PASS | 后端重启后 E2E 7 passed；真实响应里还带着 `X-Request-ID` 和 `X-Process-Time` |

### Kafka：只保留 aiokafka 并修好

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 9 | AUTO | 真实 broker 集成测试（apache/kafka:3.9.1，本地 `vj-kafka-it`） | PASS | 主会话复核：`KAFKA_INTEGRATION_BOOTSTRAP=localhost:9092 pytest tests/test_kafka_integration.py` → 16 passed（82.8s）；消息 agent 自己跑了两遍，结果相同 |
| 10 | AUTO | `KAFKA__DRIVER=confluent` 启动时直接失败，并给出迁移提示 | PASS | `KAFKA__DRIVER=confluent python -c "import core.config"` → `Value error, KAFKA__DRIVER=confluent 已不再支持……` |
| 11 | HUMAN | 至少投递一次：任何情况下都不会把还没处理、或没转投成功的记录的位点提交出去 | PASS（待审） | 独立审查逐个推演了批量提交、收回分区、提交失败、重投失败回退、事务、停止这几类情况的交错，最多只会重复处理，不会跳过 |
| 12 | AUTO | 审查在真实 broker 上复现的问题都已修复，并补了集成测试 | PASS | 慢处理函数不再被踢出消费组；事务 ID 冲突（fenced）后 `start()` 报错退出；事务内被拒收的记录不会提交位点；拒收之后换新的生产者继续发（消费端和发送端都做了） |
| 13 | AUTO | 每个 Kafka 配置项要么生效，要么明确标为不支持 | PASS | `backend/env.example` 的 Kafka 段逐项标注；独立审查核对过 |

### 文档解析

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 14 | AUTO | 超时真正生效 | PASS | 1 秒超时在 1.01s 触发（修复前要等 5.02s，而且报的是错误的错误码） |
| 15 | AUTO | 被放弃的转换线程有数量上限 | PASS | `test_markitdown_abandoned_conversions_are_capped`：超时 → 名额被占 → 下一个请求报 busy → 线程跑完后名额回来 |

### 回归与 CI

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 16 | AUTO | 模拟 CI：一份干净的分离工作区（没有 .env），装好全部扩展 | PASS | 34 个改动的 .py 文件放在一起跑 black/isort/flake8/mypy/bandit 全部通过；import 契约 5 条保持；pytest 594 passed、16 skipped（16 个都是需要 broker 的集成测试）；`uv lock --check` 通过；pip-audit 无已知漏洞 |
| 17 | AUTO | 全量测试分别在 DEBUG=true 和 DEBUG=false 下跑 | PASS | 两种都是 594 passed、16 skipped |
| 18 | HUMAN | CI 里新增的 kafka-integration job 能在 GitHub 上跑 | 未执行（推断） | 镜像、默认配置和健康检查命令都已在本地容器上验证；GitHub Actions 本身还没跑过，要等推送 |

### 变更范围

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 19 | AUTO | 没有改动约定范围以外的文件 | PASS | 对照文件清单核对过，没有越界 |
| 20 | AUTO | 每个新测试文件都已在 `backend/tests/README.md` 登记 | PASS | 12 个新测试文件全部登记 |

---

Total: 20 · AUTO: 16 | HUMAN: 4

## Gate Decision

- AUTO：16 PASS / 0 FAIL
- HUMAN：3 PASS（待审）/ 1 未执行（#18，要等推送后 GitHub 实际跑一次）
- Gate：**PASS（待你审）**

## 后续任务（本轮发现，没有改）

都记录在 design.md 第 4 节和 Decision Log，这里只列出来：

- **安全**：查询参数没有脱敏就写进了日志；JSON 解析失败的请求体会原样写进日志；CA 文件加载失败时会退回到系统信任库。
- **正确性**：
  - gRPC 出错时会丢失请求 ID；
  - `context.abort` 会被异常拦截器二次映射；
  - `path_params` 一直没有记进日志；
  - `instrument_app` 全部失败后也不会重试；
  - `BaseAPIClient` 发表单和上传文件时会带上错误的 Content-Type；
  - Redis 锁开了自动续期时，会把 `CancelledError` 漏出来；
  - S3 的错误响应如果是 `None`，会抛出 `AttributeError`。
- **工程**：
  - `HTTPException` 那条路径不做翻译；
  - 用 compose 起的环境里没有翻译；
  - Dockerfile 编译翻译失败时被悄悄吞掉；
  - `grpc_app/README.md` 写的拦截器实际不存在。

## 复盘

- **在旧代码上先跑一遍特征测试，确实能抓到问题**：主会话复核时发现，有 9 个测试依赖本机 `.env` 里的 `DEBUG=true`，到 CI 上必定失败，已退回修好。
- **lint 要像 CI 一样，把所有改动过的文件放在一起跑**：只单独检查一个文件时 mypy 通过，所有文件一起跑时就报出了 4 个错误（`test_document_parsers.py`），已修。
- **CI 装上全部可选扩展之后**，原本一直被跳过的测试开始真正运行，立刻暴露出藏了 5 个月的文档解析超时 bug，以及「aiokafka 适配器根本连不上真实 broker」的问题。
