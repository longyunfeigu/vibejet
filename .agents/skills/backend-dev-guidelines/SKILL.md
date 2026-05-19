---
name: backend-python-dev-guidelines
description: Comprehensive backend development guide for Python/FastAPI microservices. Use when creating routers, controllers, services, repositories, middleware; working with SQLAlchemy (async), Pydantic models, pydantic-settings, Sentry error tracking, dependency injection with FastAPI Depends, and async patterns. Covers layered architecture (routers → controllers → services → repositories), controller pattern, error handling, performance monitoring, testing strategies, and migration from TypeScript patterns.
---

<!-- AI-INSTRUCTIONS:START -->
> ## 🔴 AI Mandatory Rules (Must Follow)
>
> **Before** modifying backend code, you **MUST** use the `Read` tool to read the corresponding specification file:
>
> | Code Path to Modify | Required Specification File |
> |---------------------|----------------------------|
> | `api/routes/` | `resources/routing-and-controllers.md` |
> | `controllers/` | `resources/routing-and-controllers.md` |
> | `application/services/` | `resources/services-and-repositories.md` |
> | `infrastructure/repositories/` | `resources/services-and-repositories.md` + `resources/database-patterns.md` |
> | `application/dtos/` | `resources/validation-patterns.md` |
> | `api/middleware/` | `resources/middleware-guide.md` |
> | `core/config.py` | `resources/configuration.md` |
> | Error handling | `resources/async-and-errors.md` |
> | Test code | `resources/testing-guide.md` |
>
> **Execution Order**:
> 1. Identify which layer the code to be modified belongs to
> 2. Use the `Read` tool to read the corresponding specification file from the table above
> 3. Reference existing project code style
> 4. Write code that conforms to the specification
>
> ⚠️ **Writing code without reading specs = Violation!**
<!-- AI-INSTRUCTIONS:END -->

# Backend Development Guidelines

## Purpose

Establish consistent, production‑ready patterns for Python/FastAPI microservices, mapping proven TypeScript/Express patterns to Python idioms and leveraging fastapi-forge best practices.

## When to Use This Skill

Automatically activates when working on:
- Designing or modifying `APIRouter` routes and endpoints
- Building controllers, services, repositories
- Implementing middleware, exception handlers, logging/observability
- Database operations with SQLAlchemy (async)
- Error tracking with Sentry / tracing
- Input validation with Pydantic models
- Centralized configuration with `pydantic-settings`
- Backend testing with `pytest` and `httpx.AsyncClient`

---

## Quick Start

### New Backend Feature Checklist

- [ ] Router: clean route definitions, delegate to controller
- [ ] Controller: orchestrate HTTP semantics, no business logic
- [ ] Service: business rules, unit-of-work boundary
- [ ] Repository: data access via `AsyncSession`
- [ ] Validation: Pydantic models/validators
- [ ] Config: `pydantic-settings` (no raw `os.getenv`)
- [ ] Errors/Monitoring: Sentry + structured logs
- [ ] Tests: unit + API tests (pytest + httpx)
- [ ] Types: complete type hints, async first

### New Microservice Checklist

- [ ] Directory structure (see [resources/architecture-overview.md](resources/architecture-overview.md))
- [ ] Sentry init (first import) + exception handlers
- [ ] `core/config.py` using `pydantic-settings`
- [ ] Database engine + session factory (async SQLAlchemy)
- [ ] Middleware stack (request id, CORS, logging)
- [ ] Controller pattern (optional but recommended)
- [ ] Testing scaffolding (pytest, pytest-asyncio)

---

## Architecture Overview

```
HTTP Request
    ↓
Routers (routing/DI only)
    ↓
Controllers (HTTP semantics)
    ↓
Services (business logic/UoW)
    ↓
Repositories (data access/SQLAlchemy)
    ↓
Database (Postgres/MySQL/SQLite)
```

Key Principle: each layer has ONE responsibility.

See [resources/architecture-overview.md](resources/architecture-overview.md) for details and full examples.

---

## Directory Structure

```
app/
├── api/
│   ├── routes/                # APIRouter definitions only
│   ├── middleware/            # Starlette/FastAPI middleware
│   └── dependencies.py        # DI factories (services, UoW, storage)
├── controllers/               # HTTP orchestration, error mapping
├── application/
│   ├── services/              # Business logic (no HTTP)
│   └── dtos/                  # Pydantic DTOs
├── domain/                    # Entities, domain services, events
├── infrastructure/
│   ├── repositories/          # SQLAlchemy data access
│   ├── models/                # ORM entities (Declarative)
│   └── database.py            # Engine/session providers
├── core/
│   ├── config.py              # pydantic-settings
│   ├── response.py            # Unified API responses (optional)
│   └── logging_config.py      # Logging/structure
└── main.py                    # App entry: routers/middleware/handlers
```

Naming Conventions:
- Controllers: `PascalCase` (e.g., `UserController`)
- Services: `snake_case` file or `PascalCase` class (e.g., `user_service.py` → `UserService`)
- Routes: `snake_case.py` (one APIRouter per file)
- Repositories: `PascalCase + Repository` (e.g., `UserRepository`)

---

## Core Principles (7 Key Rules)

### 1. Routers Only Route, Controllers Control

```python
# ❌ NEVER: business logic in routes
@router.post("/submit")
async def submit(payload: SubmitDTO):
    # 200 lines of logic
    ...

# ✅ ALWAYS: delegate to controller
@router.post("/submit")
async def submit(payload: SubmitDTO, controller: Controller = Depends(get_controller)):
    return await controller.submit(payload)
```

### 2. Use Unified Error Handling (and Controller Pattern for Complex Flows)

```python
class ConflictError(Exception):
    pass

@app.exception_handler(ConflictError)
async def conflict_handler(_, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})

class UserController:
    def __init__(self, service: UserService):
        self._service = service

    async def create(self, payload: UserCreate) -> JSONResponse:
        user = await self._service.create(payload)
        return JSONResponse(status_code=201, content=user.model_dump())
```

### 3. Send All Errors to Sentry (or Observability Backend)

```python
import sentry_sdk
sentry_sdk.capture_exception(error)
```

Prefer global exception handlers with Sentry integration so business code stays clean.

### 4. Use `pydantic-settings`, NEVER raw `os.getenv` scattered

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    SECRET_KEY: str = Field(...)
    class Config: env_file = ".env"

settings = Settings()
```

### 5. Validate All Input with Pydantic

```python
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
```

### 6. Use Repository Pattern for Data Access

```python
class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return (await self.session.execute(stmt)).scalar_one_or_none()
```

### 7. Comprehensive Tests (Unit + API)

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_user(api_app):
    async with AsyncClient(app=api_app, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/users", json={"email": "a@b.com", "password": "12345678"})
        assert resp.status_code == 201
```

---

## Common Imports

```python
# FastAPI
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

# Validation
from pydantic import BaseModel, Field, EmailStr
from pydantic_settings import BaseSettings

# Database (async SQLAlchemy)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

# Observability
import sentry_sdk
```

---

## Quick Reference

### HTTP Status Codes

| Code | Use Case |
|------|----------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 500 | Server Error |

### Templates and Starters

**fastapi-forge** (✅ Mature) — Use as baseline for:
- Async SQLAlchemy session and models: `fastapi-forge/infrastructure/database.py`, `fastapi-forge/infrastructure/models/`
- DI and auth dependencies: `fastapi-forge/api/dependencies.py`
- Config with nested models: `fastapi-forge/core/config.py`
- Unified responses and i18n (optional): `fastapi-forge/core/response.py`, `fastapi-forge/core/i18n.py`
- Middleware patterns: `fastapi-forge/api/middleware/`
- Service/UoW patterns: `fastapi-forge/application/services/`, `fastapi-forge/infrastructure/unit_of_work.py`

---

## Anti-Patterns to Avoid

❌ Business logic in routers
❌ Direct `os.getenv` sprinkled across code (use `pydantic-settings`)
❌ Services returning `Response`/HTTP status codes
❌ Direct ORM access in controllers (bypass service/repository)
❌ Blocking I/O in async endpoints (use async drivers)
❌ Missing exception handlers/Sentry integration
❌ Returning raw ORM objects to API without DTO/schema

---

## Navigation Guide

| Need to... | Read this |
|------------|-----------|
| Understand architecture | resources/architecture-overview.md |
| Create routers/controllers | resources/routing-and-controllers.md |
| Organize services/repos | resources/services-and-repositories.md |
| Validate input (Pydantic) | resources/validation-patterns.md |
| Add Sentry/observability | resources/sentry-and-monitoring.md |
| Create middleware | resources/middleware-guide.md |
| Database patterns | resources/database-patterns.md |
| Manage config | resources/configuration.md |
| Async + errors | resources/async-and-errors.md |
| Write tests | resources/testing-guide.md |
| See examples | resources/complete-examples.md |
| Celery async tasks | resources/celery-patterns.md |
| Kafka messaging | resources/messaging-patterns.md |
| Redis caching | resources/caching-patterns.md |

---

## Resource Files

### [architecture-overview.md](resources/architecture-overview.md)
Layered architecture, request lifecycle, middleware ordering, separation of concerns. Includes full code for settings, async DB, unit of work, services, controllers, routers.

### [routing-and-controllers.md](resources/routing-and-controllers.md)
Route definitions, controller patterns, DI with Depends, response models, error mapping.

### [services-and-repositories.md](resources/services-and-repositories.md)
Service/UoW boundaries, repository patterns with async SQLAlchemy, caching, testing services.

### [database-patterns.md](resources/database-patterns.md)
Async engine/session, transactions, query optimization, N+1 prevention, migrations, locking.

### [validation-patterns.md](resources/validation-patterns.md)
Pydantic v2 DTOs, validators, discriminated unions, partial updates, pagination and generic responses.

### [async-and-errors.md](resources/async-and-errors.md)
Async concurrency, timeouts/cancellation, background tasks, global exception handlers, pitfalls.

### [middleware-guide.md](resources/middleware-guide.md)
When to use middleware vs dependencies, request-id/logging/locale, composable dependencies, ordering.

### [sentry-and-monitoring.md](resources/sentry-and-monitoring.md)
Sentry init, PII scrubbing, error capture patterns, performance spans, cron monitoring.

### [configuration.md](resources/configuration.md)
pydantic-settings unified config, nested models, env parsing, secrets management, DB URL async driver.

### [testing-guide.md](resources/testing-guide.md)
Unit/integration/API tests, dependency overrides, httpx.AsyncClient, fixtures, coverage.

### [complete-examples.md](resources/complete-examples.md)
End-to-end templates and refactoring examples ready for production use.

### [celery-patterns.md](resources/celery-patterns.md)
Celery task definitions, retry strategies, timeouts, task routing, monitoring, and Celery Beat scheduling.

### [messaging-patterns.md](resources/messaging-patterns.md)
Kafka producer/consumer patterns, message serialization, consumer groups, retry with DLQ, middleware pipeline, distributed tracing.

### [caching-patterns.md](resources/caching-patterns.md)
Redis client patterns, caching strategies (cache-aside, write-through, write-behind, refresh-ahead), TTL management, distributed locking, pub/sub.


