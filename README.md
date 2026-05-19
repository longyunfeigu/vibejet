# vibejet

`vibejet` is a FastAPI foundation library and backend scaffold for building product-specific
applications. The repository should stay focused on reusable infrastructure and architectural
patterns; concrete business requirements, PRDs, and product flows belong in downstream projects.

## What It Provides

- DDD-style layering with API, application, domain, infrastructure, core, and shared modules.
- FastAPI REST runtime with request ID, logging, locale, metrics, and health middleware.
- Async SQLAlchemy persistence, Alembic migrations, repository patterns, and Unit of Work.
- File storage ports with local, S3, and Aliyun OSS infrastructure adapters.
- Messaging adapters, retry-oriented Kafka configuration, and Celery task scaffolding.
- Optional gRPC service runtime that can reuse application-layer behavior.
- Structured logging, i18n, health checks, metrics, and tracing hooks.
- pytest, async test support, lint/type/security tooling, Docker, and Docker Compose.

## Repository Layout

```text
vibejet/
|-- backend/
|   |-- api/                 # FastAPI routes, dependencies, middleware
|   |-- application/         # DTOs, use-case services, ports
|   |-- domain/              # Pure domain entities and interfaces
|   |-- infrastructure/      # DB, repositories, external adapters, tasks
|   |-- core/                # Settings, logging, responses, exceptions
|   |-- shared/              # Cross-cutting constants and helpers
|   |-- grpc_app/            # gRPC runtime and protobuf stubs
|   |-- alembic/             # Database migrations
|   `-- tests/               # pytest suite
|-- docs/                    # Reusable architecture and workflow docs
|-- scripts/                 # Development automation scripts
`-- docker-compose.yml       # Local PostgreSQL + API + gRPC stack
```

## Quick Start

Use Python 3.11.

```bash
cd backend
cp env.example .env
# Edit .env and set SECRET_KEY.

uv venv --python 3.11 .venv
source .venv/bin/activate
uv sync --extra dev

uv run uvicorn main:app --reload
```

The REST API runs at:

- `http://localhost:8000`
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

Run the Docker stack from the repository root:

```bash
SECRET_KEY=change-me docker-compose up -d
```

Run the gRPC service locally:

```bash
cd backend
uv run python grpc_main.py
```

## Configuration

Settings use Pydantic Settings v2 with nested environment variables.

```bash
APP_NAME=vibejet
DEBUG=false
ENVIRONMENT=development
SECRET_KEY=change-me
DATABASE__URL=postgresql+asyncpg://user:password@localhost:5432/dbname
REDIS__URL=redis://localhost:6379/0
STORAGE__TYPE=local
```

See `backend/env.example` for the full set of runtime, database, Redis, storage, Kafka,
observability, gRPC, CORS, and upload settings.

## Development

```bash
cd backend

uv run pytest tests/
uv run pytest tests/ --cov=. --cov-report=term-missing

uv run black .
uv run isort .
uv run flake8 .
uv run mypy .
uv run bandit -r . -c pyproject.toml
```

Database migrations:

```bash
cd backend
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

Protocol buffers:

```bash
cd backend
bash scripts/gen_protos.sh
```

i18n:

```bash
cd backend
uv run pybabel extract -F babel.cfg -k _l -o locales/messages.pot .
uv run pybabel update -i locales/messages.pot -d locales/
uv run pybabel compile -d locales/
```

## Base Library Boundary

Keep this repository generic:

- Do not add product PRDs, launch articles, market-specific datasets, or concrete product epics as
  permanent base-library docs.
- Do not hard-code downstream business roles, policies, or workflows into shared framework code.
- Add downstream modules behind the existing layer boundaries and keep infrastructure behind ports.
- Treat generated Story/Epic plans as temporary implementation artifacts unless they describe a
  reusable convention.

## Documentation

- [Architecture](docs/architecture.md)
- [AI workflow](docs/ai-workflow.md)
- [FastAPI review checklist](docs/review-checklist-python-fastapi.md)
- [Feature plan template](docs/plans/TEMPLATE.md)
