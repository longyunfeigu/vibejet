# 0001. LLM 结构化输出能力加在端口层（LLMPort.generate_structured）

## Status

Accepted（2026-06-03，epic-3 实现期落地；决策源：epic-3 plan §2 D3/D4）

## Context

epic-3「AI 出题」要求模型输出**结构化题目**（题型/题干/选项/答案/评分要点/分值），而基座的
`application/ports/llm.py` `LLMPort` 只有 `generate()`/`stream()`，返回纯文本
（`LLMResponse.content: str`）。后续 Epic（评分、错题分析）同样会需要"按 schema 出 JSON"。

同时有一条 NFR 约束：AI 出题 P95 < 60s。基座 OpenAI 客户端默认 `timeout=60 + max_retries=2`，
最坏 ~180s，会击穿同步出题预算。

## Decision

1. **端口层扩展**：给 `LLMPort` Protocol 加
   `async generate_structured(messages, *, schema, model=None, timeout=None) -> dict`，
   `OpenAIProvider` 用 OpenAI `response_format={"type":"json_schema","json_schema": schema}` 实现，
   `json.loads` 后返回 dict。不另起客户端，复用现有生命周期（`infrastructure/external/llm/`）。
2. **独立超时预算**：该调用经 `client.with_options(timeout=eff, max_retries=0)` 覆盖默认，
   `eff = 调用方传入 timeout 或 55s 上限`，保证单次调用 < 60s NFR。
3. **失败边界两分**：
   - 基础设施异常（timeout/连接/鉴权/限流）→ 抛 `LLMUnavailableError`（定义在 port 模块，
     app/infra 均可 import 无循环依赖）→ 调用方映射 503（`QUESTION_GENERATION_UNAVAILABLE=60023`）。
   - 内容问题（非法 JSON / 字段缺失）→ **不在 provider 层处理**，`JSONDecodeError` 透传，
     由应用层按"内容不合格"（200 + status=invalid + reasons）分流。
4. **校验责任分层**：JSON-schema + Pydantic 只保**形状/类型/枚举**；跨字段业务规则
   （单选恰好 1 个正确答案、score>0、客观题 options 非空、简答必须有 scoring_points）
   归 **domain service**（`domain/question/service.py`）。

## Consequences

- 出题（epic-3）与未来评分/分析共用一个结构化出口，调用方不再各自解析纯文本。
- 端口签名是内部契约：新 provider（Azure/vLLM 等）实现时必须同样遵守
  "基础设施异常 → `LLMUnavailableError`、内容问题透传"的边界。
- `openai` 由此首次成为显式直接依赖（`pyproject.toml: openai>=1.40,<2`）——此前 provider
  顶层 import 但依赖清单缺失（懒加载掩盖的潜伏缺陷），epic-3 T002 修复。

## Alternatives Considered

- **只在 application 层解析纯文本 JSON（Rejected）**：不改端口，由每个调用方对
  `generate()` 的文本自行 `json.loads` + 校验。解析脆（没有 provider 级 schema 约束）、
  复用差（出题/评分各写一遍），且无法统一基础设施失败语义。
- **出题走异步任务 + 轮询（Rejected，D4）**：Story AC 是同步形态（`→ 200 + questions[]`），
  P95<60s 预算下同步足够；Celery + 任务表是过度设计。
