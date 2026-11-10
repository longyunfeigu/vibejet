# vibejet Architecture

`vibejet` is a FastAPI foundation library and application scaffold. It should provide reusable
technical building blocks, not a finished product domain. Downstream projects own their specific
business modules, policies, roles, workflows, and product requirements.

## Goals

- Provide a production-oriented backend base for REST, gRPC, persistence, storage, messaging,
  background tasks, i18n, observability, and testing.
- Keep domain code independent from FastAPI, SQLAlchemy, SDKs, queues, and other infrastructure.
- Make downstream business code easy to add without changing the core framework shape.
- Keep documentation generic unless it describes a reusable platform capability.

## Non-Goals

- Do not define product PRDs, personas, growth loops, market-specific flows, or other
  application-specific requirements in this base repository.
- Do not put concrete business decisions into shared exceptions, response codes, middleware, or
  framework utilities.
- Do not make generated story or epic artifacts permanent baseline docs for the base library.

## Layering

The backend follows DDD-style layering with hexagonal boundaries.

```text
api -> application -> domain
infrastructure -> application/domain interfaces
```

`domain/`
: Pure entities, value objects, domain services, repository interfaces, and domain exceptions.
  It must not import `api`, `application`, `infrastructure`, FastAPI, SQLAlchemy, Redis, Kafka,
  storage SDKs, or LLM SDKs.

`application/`
: Use-case orchestration, DTOs, transaction boundaries, and ports. Application services coordinate
  domain objects and depend on interfaces rather than concrete infrastructure implementations.

`infrastructure/`
: SQLAlchemy models, repository implementations, external clients, storage providers, messaging
  drivers, Celery tasks, and concrete adapters for application ports.

`api/`
: FastAPI routes, dependencies, middleware, request parsing, response formatting, and HTTP error
  translation. Routes should stay thin and delegate use cases to `application/`.

`core/`
: Configuration, logging, exception handlers, observability helpers, and response primitives that
  are shared by the runtime.

`shared/`
: Cross-cutting constants and small utilities that do not belong to a specific domain.

## Current Foundation Capabilities

The base library currently provides these reusable capabilities:

| Capability | Main Paths | Notes |
|------------|------------|-------|
| REST runtime | `backend/main.py`, `backend/api/` | FastAPI app, versioned routes under `/api/v1`, middleware, OpenAPI |
| gRPC runtime | `backend/grpc_app/`, `backend/grpc_main.py` | Parallel transport for services that need gRPC |
| Persistence | `backend/infrastructure/database.py`, `backend/alembic/` | Async SQLAlchemy and Alembic migrations |
| Repository/UoW | `backend/domain/*/repository.py`, `backend/application/ports/unit_of_work.py`, `backend/infrastructure/repositories/`, `backend/infrastructure/unit_of_work.py` | Domain repository interfaces, application transaction port, and SQLAlchemy implementations |
| File storage | `backend/application/ports/storage.py`, `backend/infrastructure/external/storage/` | Local, S3, and OSS providers behind a storage port |
| Messaging（参考脚手架，未接线） | `backend/infrastructure/external/messaging/` | Kafka publisher/consumer，唯一驱动 aiokafka（confluent 驱动已移除），带 retry 分层 topic 与 DLQ；未到期的重投只暂停所在分区，重投/DLQ 发送失败时暂停该分区并退避后重新消费（不越过失败记录），位点批量提交（撤销/停止时冲刷），可选事务性重投，`publish_many` 先全部发出再一起等送达；handler 跑在独立线程上（心跳不断），重投 producer 被隔离时 `start()` 报错退出。投递语义为至少一次：`publish_many` 失败后整批重试、重投超时都可能产生重复。aiokafka 0.13 已知限制（探针发现，上游 aio-libs/aiokafka#1017 是同一症状）：broker 拒收一条记录后，幂等 producer 在该分区上的序号再也对不上（OutOfOrderSequenceNumber）；绕法是消费者每次重试前换新的重投 producer，发布者遇到 OutOfOrderSequenceNumber/UnknownProducerId 时换新 producer（触发的那次调用仍报 PublishError）。依赖为 optional extra `aiokafka`，docker-compose 无 broker，运行时零接线——使用前需装 extra 并自行装配 |
| Background tasks（参考脚手架，未接线） | `backend/infrastructure/tasks/` | Celery app, task base, and dispatcher pattern。celery 为 optional extra，无 worker/beat 编排，运行时零接线 |
| Observability | `backend/core/observability/`, `backend/api/routes/health.py`, `backend/api/routes/metrics.py` | Health checks, metrics, tracing hooks |
| i18n | `backend/core/i18n.py`, `backend/locales/` | Babel-based message catalogs |
| Testing | `backend/tests/`, `backend/pyproject.toml` | pytest, async test support, repository and config tests |

If a capability starts to encode one application's business language, move that code into the
downstream project or mark it as an example that can be removed.

## Extension Rules

When adding a new downstream business module:

1. Add domain objects under `backend/domain/<module>/`.
2. Add repository interfaces in the domain layer.
3. Add application services and DTOs under `backend/application/`.
4. Add infrastructure models, repositories, external clients, and migrations under
   `backend/infrastructure/`.
5. Add HTTP routes under `backend/api/routes/` and register them in `backend/main.py`.
6. Add tests under `backend/tests/`.

Keep the dependency direction unchanged. If an application service needs an external system, define
a port in `application/ports/` and implement it in `infrastructure/`.

Unit of Work is an application-layer transaction boundary. The central UoW port must stay
repository-agnostic; application services should type the specific repositories they need with
service-local protocols instead of expanding one global UoW interface for every new module.

## Documentation Rules

- Keep repo-level docs focused on reusable architecture, development workflow, review standards,
  and planning templates.
- Product PRDs, epics, routing datasets, launch articles, and app-specific examples should live
  in downstream application repositories.
- Temporary implementation plans can be created under `docs/tasks/plans/`, but they should be removed or
  archived once they are no longer useful as reusable guidance.
- If a generated doc describes a concrete app, do not treat it as part of the base library baseline.
