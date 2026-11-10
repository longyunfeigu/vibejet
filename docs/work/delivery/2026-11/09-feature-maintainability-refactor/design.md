# 技术设计 — 可维护性：消除超复杂度函数，Kafka 只保留 aiokafka

> 由 `/feature-design` 产出。范围和 Kafka 驱动这两道关卡由你在对话里亲自选定；其余关卡是「自动确认，待你审」，见文末 Decision Log。

| 关卡 | 结论 | 依据 |
|---|---|---|
| 范围 | 12 个超复杂度函数全部重构 | **你选定**（AskUserQuestion） |
| Kafka 驱动 | 保留 aiokafka，删除 confluent | **你选定**（AskUserQuestion） |
| 分级 | 混合：T5 横切重构 + T3 冲突变更（默认驱动变了）+ T6 外部依赖变更（删除 confluent-kafka） | 自动确认，待审 |
| 测试策略 | 先写特征测试，并在旧代码上跑通；CI 改为安装全部可选扩展 | 自动确认，待审 |

Feature: 可维护性治理——复杂度、重复度
Type: 混合 T3 + T5 + T6
Date: 2026-11-09
Branch: `feat/import-voice-agent-delivery`

---

## 1. 背景

「代码质量」评估里，可维护性被评为「中」。2026-11-09 实测：

- **复杂度**：后端有 12 个函数超过 `.flake8` 的 `max-complexity = 10`，最高 46。其中 11 个测试覆盖为 0%，另一个 11%。
- **为什么一直没人发现**：CI 只 lint 改动过的文件，这些文件一直没人动，所以超标从来没报出来。
- **重复度**（jscpd，至少 6 行、60 个 token 才算重复）：后端 2.36%（428 行，31 处），前端 0%。最大的几处是 ORM 模型的通用字段、S3 与 OSS 提供者之间、两个 LLM 提供者之间的重复。

| 函数 | 复杂度 | 所在位置 | 处理 |
|---|---|---|---|
| `AiokafkaConsumer.start` | 46 | Kafka（aiokafka） | 重构 |
| `KafkaConsumer.start` | 38 | Kafka（confluent） | 随 confluent 删除 |
| `KafkaPublisher.publish` / `publish_many` | 13 / 13 | Kafka（confluent） | 随 confluent 删除 |
| `BaseAPIClient._request` | 15 | HTTP 客户端基类（仓库内无人调用，留给下游用） | 重构 |
| `LoggingMiddleware.__call__` | 14 | 每个 HTTP 请求都会经过 | 重构 |
| `RedisClient.lock` | 13 | 分布式锁（仓库内无人调用，留给下游用） | 重构 |
| `LoggingInterceptor` / `ExceptionMappingInterceptor.intercept_service` | 12 / 11 | gRPC | 重构 |
| `S3Provider.upload` / `MiddlewareStorage.upload` | 12 / 12 | 文件上传 | 重构 |
| `instrument_app` | 11 | 链路追踪 | 重构 |

## 2. 方案

1. **删除 confluent 驱动**，aiokafka 成为唯一驱动，3 个超标函数随之消失。
   - `KAFKA__DRIVER` 配置项保留：不认识的配置项会让启动直接失败，删掉它会让下游现有的 `.env` 起不来。
   - 默认值改为 `aiokafka`；如果配成 `confluent`，启动时报一条明确的错误，告诉用户改用 aiokafka。
2. **其余 9 个函数逐个重构**，每个都按同一套步骤：
   - 先写特征测试，覆盖所有分支，在旧代码上跑通；
   - 再拆函数（提取辅助函数、提前返回、改用查表），把复杂度降到 10 以下；
   - 拆完后同一批测试必须照样通过；
   - 被改动文件里原有的 lint 和类型问题一并清掉（CI 会对改动过的文件整体做检查）。
3. **CI 装上全部可选扩展**：`uv sync --extra dev` 改为 `uv sync --all-extras`。不装的话，gRPC、Kafka、存储、可观测性这些适配器的测试在 CI 里都会被跳过，等于没测。
4. **防止复杂度回升**：重构完成、超标数降到 0 后，CI 增加一步，对整个后端只跑复杂度检查（`flake8 --select C901`），任何新增超标都会让 CI 失败。
5. **重复度**：本次只做量化。2.36% 低于常见的 3% 警戒线，而占比最大的 ORM 字段重复一旦改动就会牵涉数据库结构，按 strict 处理，不在本次范围。CI 增加 jscpd 门禁，重复度超过 3% 即失败。

**分工**（三个 agent 并行，文件互不重叠）：
- HTTP / gRPC / 链路追踪：4 个函数
- 存储 / 缓存 / HTTP 客户端：4 个函数
- 消息：删除 confluent，重构 aiokafka 的消费者启动逻辑

由主会话负责：设计文档、CI、`tests/README.md` 索引、文档解析的超时 bug（见 §4），以及最终验收。

## 3. 影响面与风险

- **对外行为变化只有 Kafka 默认驱动这一处。** 下游项目如果用的是 confluent，必须迁到 aiokafka，或者自己把 confluent 驱动加回去。
- 其余重构都要求可观察行为不变，由特征测试兜底。
- **残余风险**：可选适配器在本地没有真实的 Kafka、gRPC、S3、Redis 服务，测试只能用假对象模拟外部系统，证明的是「调用这些外部系统的方式没变」，证明不了「和真实服务配合仍然正常」。
- **可回滚**：按 commit 粒度 revert。

## 4. 实施中发现的已有问题

**文档解析的超时从来没生效过。**

- 装上 documents 扩展后，`test_markitdown_parse_timeout_is_mapped` 失败：期望报 `document.parse.timeout`，实际报的是 `document.parse.empty_content`。
- 原因：`backend/infrastructure/external/parsing/providers/markitdown.py` 用 `anyio.fail_after` 包住 `anyio.to_thread.run_sync`，但没有传 `abandon_on_cancel=True`。线程里的等待取消不了，超时形同虚设，接口会一直等到转换做完。
- 这个测试 2026-06-10 加入，因为 CI 从没装过 documents 扩展，一直被跳过。
- 修法：传入 `abandon_on_cancel=True`，等待可以被放弃。线程本身本来就取消不了，只是不再等它；这和测试里写明的意图一致。
- **审查补充**（独立审查 agent 实测）：被放弃的线程会把线程池的名额还回去，但自己还在继续跑。反复超时的话，后台转换线程会没有上限地堆积：实测 60 次超时后有 61 个线程还活着。旧代码的上限是 40 个线程，但每个请求都会卡死，还会占满 S3 等调用共用的线程池。
- **加上并发上限**：转换线程在线程内先占一个名额，跑完才释放（进程内共 4 个，`_MAX_CONCURRENT_CONVERSIONS`）。名额满了直接报 `document.parse.busy`，被放弃的线程在跑完之前一直占着名额。这个错误码会写进 `Document.error_code`，不走翻译表。配了一条测试来验证：超时 → 名额被占住 → 再来请求报 busy → 线程跑完后名额回来。

**HTTP / gRPC / 链路追踪重构时发现的已有问题。** 这些问题由特征测试原样固定下来，本次不改，列为**后续任务**：

1. gRPC 出错时，请求 ID 会丢：异常拦截器写的 trailing metadata 把 `x-request-id` 覆盖掉了（在真实的 gRPC 1.78 上复现过）。
2. 服务方自己调用 `context.abort` 时，异常拦截器仍会接住它，记一条带误导性的 `grpc_mapped_error`（错误码 40000），然后再 abort 一次。客户端收到的状态码不受影响。
3. HTTP 日志中间件取请求信息时，FastAPI 还没完成路由，所以 `path_params` 永远记不下来。
4. **敏感信息会写进日志**：
   - 查询串先被解码再解析，编码过的 `&`、`=` 会把一个参数切成几个；
   - 查询参数不做脱敏，`?token=...` 会原样写进日志。
5. **敏感信息会写进日志**：JSON 请求体解析失败（包括被截断的）时，会不脱敏地按原文记录。前提是开着 DEBUG，所以暴露面有限。
6. `instrument_app` 即使 4 个插桩全部失败，也会把自己标记为「已插桩」，之后不会再重试。

另外，`grpc_app/README.md` 里列出的 authorization 拦截器并不存在，属于文档和现实不一致。

**存储 / 缓存 / HTTP 客户端重构时发现的已有问题。** 这些问题由特征测试原样固定下来，本次不改，列为**后续任务**：

1. **`BaseAPIClient` 发表单和上传文件时会出错**：默认的 `Content-Type: application/json` 会盖掉表单和 multipart 的类型，文件上传时 multipart 的分隔符因此丢失。
2. `RedisClient.lock` 开了自动续期时，如果锁内代码一次都没有 await，`CancelledError` 会漏出来，锁也不会被释放。
3. S3 SDK 的错误如果 `response` 属性是 `None`，`_handle_exception` 会抛出 `AttributeError`，而不是 `StorageError`。

**附带改动**：
- `storage/base.py` 里的 `stream_download` 改成用普通 `def` 声明、返回异步迭代器。这修掉了 mypy 的误报。
- 副作用是：现有测试 `test_storage_upload_stream_abort.py` 里的假实现写成了协程，按完整的 mypy 检查会多出 4 个类型错误。CI 只检查改动过的文件，所以现在看不到；以后谁改到这个测试文件，要顺手把假实现改成异步生成器。
- md5 调用加上了 `usedforsecurity=False`，算出来的摘要不变；在 FIPS 环境下，md5 从「直接报错」变成「可以用」。
- **审查补充**（Redis 锁的后续任务）：锁内代码如果在第一次 await 之前就抛出 `ValueError`，调用方收到的是 `CancelledError` 而不是 `ValueError`，锁也要等 TTL 过期才释放。影响面小：自动续期默认关闭（`core/config.py:429`），仓库里也没有地方调用 `lock()`。

## 5. 提交计划与回滚耦合

独立审查发现，CI 的改动依赖其他几部分改动，必须一起落地：
- 全后端复杂度检查要等消息模块的重构完成才会通过；
- 装上全部扩展之后，文档解析的测试会开始运行，必须先修好超时问题才会通过。

所以 **CI 的改动放在最后一个提交**。之后如果只 revert 消息模块或 markitdown 修复，CI 会变红，需要连同 CI 的那个提交一起 revert。

建议的提交顺序（等你同意后再提交）：
1. `fix(document)`：markitdown 超时生效 + 并发上限
2. `refactor(http, grpc, tracing)`：4 个函数 + 3 个测试文件
3. `refactor(storage, cache, api-client)`：4 个函数 + 4 个测试文件
4. `refactor(messaging)`：删除 confluent，重构 aiokafka，修复 bug，补齐能力，加集成测试（几个步骤改的是同一批文件，没法按文件拆开，合成一个提交，在提交说明里分段写清楚）
5. `ci`：装全部扩展、复杂度门禁、重复度门禁，以及 Kafka 集成测试的 job。集成测试 job 用 `apache/kafka:3.9.1` 作为 service 容器，和本地验证用的镜像、默认配置完全一致：单节点 KRaft，事务日志副本数为 1，所以单 broker 上也能跑事务。通过环境变量 `KAFKA_INTEGRATION_BOOTSTRAP=localhost:9092` 打开这组测试。

**执行记录**：负责消息模块的 agent 做到 4 项能力的一半时，连续两次请求超时，于 2026-11-10 停掉。由一个新的 agent 接手，从当前代码状态继续：当时 24 个测试失败，有 4 个 mypy 错误。
6. `docs(delivery)`：设计文档、检查清单、`tests/README.md`

审查里的两个 nit 已确认，不改：
- gRPC 异常拦截器取 `error_type` 的时机提前了一点。只有在 `error_type` 不存在的对象上才会表现出差别，而 `BusinessException` 一定会设置它，所以实际碰不到。
- jscpd 用 `npx` 固定了 4.0.5 版本，但它自己的依赖没有锁定。属于可以接受的风险。

---

## Decision Log

### 自动确认的关卡

分级、测试策略、复杂度门禁、重复度门禁、文档解析超时的修法：`Gate: auto-confirmed — pending user review`。

### 范围 — Decision Discussion

**Decision point (option comparison)**：
- 只重构核心路径，其余锁基线
- 12 个全部重构
- 只加基线和 CI 检查，不重构

**Decision**：12 个全部重构（**你选定**）。

### Kafka 驱动 — Decision Discussion

**Decision point (option comparison)**：
- 保留 confluent，删除 aiokafka
- 两个都保留
- 保留 aiokafka，删除 confluent

**Additional context**：confluent 原本是配置默认值。aiokafka 是纯 Python 的 asyncio 实现，不依赖 librdkafka。
**Decision**：保留 aiokafka，删除 confluent（**你选定**）。

### Kafka 驱动（实施中追加）— aiokafka 适配器本身跑不通 — Decision Discussion

**Decision point (option comparison)**：修好 aiokafka 并继续只保留它 / 改为保留 confluent / 两个都保留。
**Additional context**：实施时发现，aiokafka 适配器拿真实的 aiokafka 0.13.0 一跑就出错，共 4 处。主会话已对照库的接口逐条核实：

1. 发送端传了 aiokafka 不认识的 `batch_size`、`max_in_flight_requests_per_connection`（`publisher.py:70`、`publisher.py:72`），每次创建都会报错。
2. 默认压缩方式是 `zstd`（`core/config.py:60`），但没装 zstd 编解码库。
3. 订阅时传的不是 `ConsumerRebalanceListener` 实例（`consumer.py:165`）；出错时，已经启动的消费者没有被停掉。
4. 暂停、恢复分区时传的是列表，aiokafka 要求逐个传分区（`consumer.py:187`、`consumer.py:193`）。

这些问题以前没被发现，是因为 Kafka 代码的测试覆盖率一直是 0%，CI 也从没装过这个扩展。
**Decision**：修好 aiokafka，继续只保留它（**你选定**）。

**实施顺序**：
1. 写特征测试，把当前行为（包括这 4 个 bug）原样固定下来；
2. 重构；
3. 修 bug，并把对应测试改成断言正确行为；
4. 用真实 broker 跑一遍集成测试，证明确实「修好了」。CI 里通过 service 容器运行这项测试。

### CI 装全部可选扩展 — Decision Discussion

**Decision point (option comparison)**：
- 可选扩展的测试在 CI 里跳过（现状）
- CI 装上全部扩展，让这些测试真正运行

**Rationale**：要重构的函数大多在可选适配器里。测试在 CI 里被跳过，就保护不了重构。这次装上后，立刻测出了一个藏了 5 个月的超时 bug。代价是 CI 安装时间变长。
**Decision**：装全部扩展。`Gate: auto-confirmed — pending user review`。

### Kafka（实施中追加）— 补回 aiokafka 缺的能力 — Decision Discussion

**Decision point**：删掉 confluent 之后，aiokafka 适配器和原来的 confluent 版本相比少了 4 项能力（主会话已核实）：
1. 延迟重试用 `asyncio.sleep` 卡住整个消费循环。重试最长一档是 10 分钟，超过了 aiokafka 默认的 `max_poll_interval_ms` 300 秒，消费者大概率会被踢出消费组。
2. 一些配置项被忽略：`max_poll_interval`、`session_timeout`、`fetch_min/max`；另外没有开启幂等发送。
3. 没有事务性重投：`KAFKA__TRANSACTIONAL_ID` 配了也不起作用。
4. 没有批量提交和批量发送。

**Decision**：本轮全部补齐（**你选定**）。

**实施顺序**：修 4 个崩溃 bug → 1 → 2 → 3 → 4 → 真实 broker 集成测试。

### 旧配置 `KAFKA__DRIVER=confluent` — Decision Discussion

**Decision point (option comparison)**：
- 启动即失败，加迁移说明
- 只打告警，等真正用到 Kafka 时才报错（会留下「能配但不能用」的墓碑）

**Decision**：启动即失败，加迁移说明（**你选定**）。

### Kafka（实施中追加）— 重投失败会悄悄丢消息 — Decision Discussion

**Decision point (option comparison)**：
- 本轮修掉
- 只记为残余风险

**Additional context**：接手消息模块的 agent 发现了这个问题，主会话在原始代码里核实过。往重试 topic 或死信 topic 发送失败时，代码只打一条日志「message will be redelivered」，然后继续处理下一条。同一分区的下一条消息一提交位点，失败的那条就被跳过去了，实际上不会重投。原来的两个驱动都有这个问题。
**Rationale**：这是悄悄丢消息，和「至少投递一次」的承诺矛盾，日志内容也不属实。你定的方向是把 aiokafka 修到真正能用，而这处修法很小，复用延迟重试已有的「暂停分区」机制即可。
**Decision**：本轮修掉。做法是失败时不推进位点，暂停该分区并回退到失败的那条，等一段退避时间后重新消费；其他分区不受影响。`Gate: auto-confirmed — pending user review`。

### 消息模块独立审查 — 处理决定

审查结论：「至少投递一次」能保证住，所有不好的交错情况最多造成重复处理，不会跳过消息，没有阻断项。审查在真实 broker 上证实了以下问题，本轮处理：

1. **心跳被饿死（相对 confluent 是退步）**：同步处理函数和 aiokafka 的心跳任务跑在同一个事件循环上，处理时间一旦超过 `SESSION_TIMEOUT_MS`（默认 45 秒），消费者就会被踢出消费组，同一条消息会被重复处理。`env.example` 里说「处理时间受 `MAX_POLL_INTERVAL_MS` 约束」，这和实际不符。修法：把处理函数挪到线程池里执行，让心跳不受影响。
2. **事务 ID 冲突后会无声地无限重试**：两个实例用了同一个 `KAFKA__TRANSACTIONAL_ID`，后启动的会把先启动的「隔离」（fence）掉。被隔离的那个之后每次重投都会失败，失败后又被当成可重试的错误，于是那个分区永远卡住，进程看上去却一切正常。多个副本共用同一份 env 文件时很容易碰到。修法：把被隔离当成致命错误，停掉客户端，让 `start()` 直接报错退出；同时在文档里写明事务 ID 必须每个实例唯一。
3. **驱动配置报错**：「启动即失败」是你已经拍板的，保留。改的是报错内容：除了 `aiokafka` 以外的任何值（包括 `AIOKAFKA`、`kafka`），都给出同一条迁移提示，并写出实际读到的值。
4. 发送端构造失败时，事件循环线程没有关掉、生产者也没有关闭，存在泄漏。修。
5. 从未启动过的消费者不会关闭它的事件循环。修。重复调用 `start()` 时给出明确的报错。
6. `publish_many` 中途失败：非超时类的发送错误统一包装成 `PublishError`；文档里写明，失败前已经进入发送队列的那部分消息仍可能被发出去，所以整批重试会造成重复。
7. 补测试：
   - 同一分区里，第 N 条已确认、第 N+1 条重投失败，此时第 N 条的位点要正常提交，第 N+1 条不能被跳过；
   - 事务中止后，位点不提交，换一个新事务重试；
   - 修正测试文件里已经过时的说明文字。

**修复过程中又在真实 broker 上发现两个问题**（消息模块 agent 用探针复现）：

8. **事务性重投会丢数据**：事务里调用了 `send()`，却没有等待投递结果。broker 拒收这条记录时，事务照样提交，源 topic 的位点也一起提交了，结果死信消息丢了，源消息却被标记为已处理。修法：在事务内等待投递结果，被拒收就中止事务。
9. **aiokafka 0.13 的幂等序号无法恢复**：一个批次被拒收后，aiokafka 不会重置该分区的序号，之后往这个分区的所有发送都会报 `OutOfOrderSequenceNumber`，永远发不出去。事务模式会这样；只开幂等、且该分区已经写过数据时也会这样。
   - **消费端**：一次非致命的重投失败后，换一个新的重试/死信生产者再试，新生产者有新的 producer id 和从 0 开始的序号（Java 客户端内部也是这么做的）。被隔离（fenced）和事务致命错误仍然直接让 `start()` 报错退出，不会重建。
   - **发送端**（主会话决定一并修，`Gate: auto-confirmed — pending user review`）：只在遇到 `OutOfOrderSequenceNumber` 或 `UnknownProducerId` 时重建生产者，本次调用方照样收到 `PublishError`，不会悄悄重试。重建在并发调用下是安全的，旧的生产者会被关闭。理由：默认开启幂等是这一轮才加的，在这之前发送端连创建都会失败，所以不存在需要保持的旧行为；而一条消息被拒收就让整个分区在进程整个生命周期里都发不出去，作为默认行为不能接受。

**后续任务**（本轮不改）：CA 文件加载失败时，会悄悄退回到系统信任库。这是原本就有的行为，应该改成加载失败直接报错；本轮只把 `env.example` 里的说明改成「已知限制」。

## 迁移说明（给已有项目）

- **配置**：`.env` 里如果有 `KAFKA__DRIVER=confluent`，改成 `KAFKA__DRIVER=aiokafka`，或者直接删掉这一行（默认就是 aiokafka）。不改的话，应用启动时会报 `KAFKA__DRIVER=confluent 已不再支持……`，然后退出。这一点和项目有没有用 Kafka 无关。
- **依赖**：可选扩展 `kafka`（confluent-kafka）已删除；要用 Kafka，安装 `aiokafka` 扩展。
- **其他取值**：`KAFKA__DRIVER` 现在只接受 `aiokafka`。以前任何不是 `aiokafka` 的值都会被悄悄当成 confluent，现在会直接报错。
