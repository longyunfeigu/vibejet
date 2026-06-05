# 0002. 文档驱动 grounded 出题：切块 + map-reduce 提取（BackgroundTasks）+ 忠实闸

## Status

Accepted（2026-06-04；决策源：本会话 reference-impl 研究 + plan `docs/tasks/plans/2026-06-04-grounded-doc-question-generation-plan.md`）

## Context

原实现两处缺陷：

1. **出题脱离原文**：`generate` 只用「考试目标六字段 + 已确认知识点名」喂 LLM，**不含资料原文**。
   题目细节由模型基于知识点名脑补，无法引用资料具体表述、易脱离资料编造。
2. **大文档会炸**：知识点提取整篇 `material.content` 喂 LLM（`knowledge_extraction.py`），
   文档超 LLM 上下文即失败；出题同理（一旦带原文）。

业界做法（检索 2025 文献 + 开源）：RAG-grounded generation——检索/遍历原文片段 → 锚定原文生成 →
忠实度校验。其中对「覆盖整篇文档」的出题任务，**map-reduce > top-k 向量 RAG**（RAG 按相关性
检索会系统性漏掉未命中章节，覆盖不全）。

## Decision

选定档位 **B1**：map-reduce + 字面匹配，**不引入 embedding/向量库**。

1. **录入即切块**：`split_into_chunks`（字符滑窗 + overlap，纯 domain 函数）在 `create_material`
   时切分全文，持久化到 `material_chunks`（稳定 FK，提取与出题共用）。
2. **提取改 map-reduce**：每 chunk 独立抽知识点名（map，`Semaphore(4)` 限并发 + `wait_for(30s)`
   超时），跨 chunk 去重（reduce）。解决超上下文；部分 chunk 失败不拖垮整体，全失败才 `failed`。
3. **异步换 FastAPI BackgroundTasks**（仅 KP 提取；email 仍 Celery）：提取逻辑下沉为
   application service 纯方法 `run_extraction(material_id, llm)`，dispatch 交路由的
   `BackgroundTasks`。`trigger` 幂等（已 processing 不重复调度）。
4. **grounded 出题**：出题前按已确认 KP 名**字面匹配**选相关 chunk（保序去重，上限 12；无命中
   回退前 N；无 chunk 降级），注入 prompt 作原文依据；schema 每题加 `source_quote`（逐字摘录）。
5. **忠实闸（第三道闸）**：在现有形状闸 + domain 闸后，加 `collect_faithfulness_issues`——
   每题 `source_quote` 归一化后须为某 chunk 子串，否则该批 `invalid`（200，不落库）。空 quote /
   无 chunk 降级跳过。`question.source_quote` 持久化（审计/可追溯）。

## Consequences

- 出题锚定原文，可追溯来源；脱离资料编造的题被忠实闸拦截。
- 大文档提取/出题不再超上下文。
- 去掉 KP 提取的 Celery broker/worker 运维负担。**代价**：BackgroundTask 跑在 web 进程内，
  进程重启即丢任务（material 卡 processing）——靠前端 60s 超时 + 重新触发兜底；低并发 admin 场景可接受。
- `material_chunks` 表 + `question.source_quote` 列（两个 migration）。
- 提取/出题用 KP 名字面匹配定位 chunk，命中率依赖 KP 名是否出现在原文（KP 由原文抽取，通常命中）。

## Alternatives Considered

- **top-k 向量 RAG（QuizardApp 式，Rejected）**：出题要覆盖全文，top-k 按相关性检索会漏覆盖未命中章节；
  且需 embedding + 向量库基建。map-reduce 用人工已确认 KP 列表作覆盖锚，无需向量库。→ 升级条件保留：
  KP 名字面命中率过低时再上 embedding（B2）。
- **保留 Celery（Rejected）**：用户要求换 BackgroundTasks 去掉 broker/worker；提取属低并发 admin 触发，
  in-process 可接受。email 任务仍用 Celery，基建保留。
- **存 KP→chunk provenance 指针（Rejected）**：确认流程是「按名称全量替换」，会丢 provenance；
  改用生成时 KP 名字面匹配 chunk，免改确认流程、免给 knowledge_point 加列、统一处理人工新增 KP。
- **出题也异步化（Rejected，本期）**：KP 锚定后出题 prompt 已收敛为单次调用，同步足够；不后台化。
