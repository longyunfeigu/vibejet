---
name: vibejet-backend-dev-guidelines
description: Repo-specific backend development guardrails for vibejet. Use before modifying backend FastAPI routes, application services, domain entities, repositories, config, errors, auth, migrations, tests, observability, caching, Celery, messaging, LLM, storage, or external integrations.
---

# Vibejet Backend Development Guidelines

Use this skill when changing anything under `backend/` or backend-facing docs/contracts.

This skill is not a generic FastAPI template. It is a loader for vibejet's backend architecture rules. The repo docs and existing code win over any generic example.

## Required First Read

Before modifying backend code, read:

1. `resources/backend-constitution.md`
2. The relevant layer resource below
3. Any risk resource whose trigger matches the change
4. Before finishing, `resources/review-gate.md` and `docs/reference/guides/review-checklist-python-fastapi.md`

## Conflict Priority

When guidance conflicts, use this order:

1. User's current task and acceptance criteria
2. `AGENTS.md`, `CLAUDE.md`, `docs/project/architecture.md`
3. Stable contracts under `docs/project/api/`, `docs/project/data/`, and ADRs
4. Existing production code patterns and tests
5. This skill's resources
6. Generic FastAPI / SQLAlchemy best practices

Do not introduce a pattern because it appears in a generic resource if the current repo does not use it.

## Layer Resources

Read `resources/backend-constitution.md` first, then:

| Change area | Required resource |
| --- | --- |
| `backend/api/routes/`, `backend/api/dependencies.py`, route registration | `resources/api-routes.md` |
| `backend/application/services/`, `backend/application/dto.py`, `backend/application/dtos/`, `backend/application/ports/` | `resources/application-services.md` |
| `backend/domain/` | `resources/domain.md` |
| `backend/infrastructure/models/`, `backend/infrastructure/repositories/`, `backend/infrastructure/database.py`, `backend/infrastructure/unit_of_work.py` | `resources/infrastructure-repositories.md` |
| `backend/infrastructure/security/`, JWT helpers, token signing/parsing, password/security utilities | `resources/security-jwt.md` |
| `backend/core/config.py`, settings, environment parsing | `resources/configuration.md` |
| Tests under `backend/tests/`, or task-doc bare `tests/...` paths in a backend Unit | `resources/testing.md` |
| `backend/core/exceptions.py`, response/error/logging/metrics/tracing/middleware error flow | `resources/errors-observability.md` |

Controller policy: controller is not a default layer in this repo. Routes normally delegate directly to application services. Add a controller only when an existing module already uses that pattern or a reviewed design explicitly requires a separate HTTP orchestration layer.

## Risk Resources

Load these when the change touches the trigger. Risk resources can matter more than layer resources because production bugs often cross layers.

| Trigger | Required resource |
| --- | --- |
| Auth, role, owner, tenant, resource visibility, public endpoint | `resources/permissions.md` |
| JWT, token claims, signing/verification, password hashing, auth cryptography/security helper | `resources/security-jwt.md` |
| DB transaction plus storage/network/queue/LLM side effect | `resources/transaction-side-effects.md` |
| Idempotency keys, retries, duplicate requests, locks, state transitions, race conditions | `resources/idempotency-concurrency.md` |
| HTTP clients, SDKs, object storage, payment/email/third-party systems | `resources/external-systems.md` |
| ORM model, Alembic migration, indexes, constraints, persistent schema | `resources/migrations.md` |
| Redis, cache keys, TTL, invalidation, distributed locks | `resources/caching.md` |
| Celery, Kafka, background workers, async dispatch, DLQ/retry | `resources/messaging-celery.md` |
| LLM output, prompts, files, untrusted metadata, external model/tool output | `resources/llm-trust-boundary.md` |

## Working Loop

1. Identify the layer and risk triggers.
2. Read the required resources and nearby existing code.
3. Implement the smallest vertical slice that satisfies the task.
4. Keep domain rules in `domain/`; keep use-case orchestration in `application/`; keep ORM/SDK details in `infrastructure/`; keep HTTP I/O in `api/`.
5. Add or update focused tests for behavior and risk.
6. Run the narrowest meaningful verification.
7. Use `resources/review-gate.md` before reporting done.
