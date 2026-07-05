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

## Authentication (OAuth Login)

Username/password auth always works. On top of it, three federated providers can be enabled
**per provider**: **Google**, **Feishu** (飞书, `open.feishu.cn`) and **Lark** (international,
`open.larksuite.com`). All of them go through the same backend pipeline (exchange the provider's
authorization code for a trusted identity → find/link/create a user → issue **our own** JWT pair),
so everything downstream is identical to password login.

Every provider is **fail-closed**: if its backend credentials are missing it is simply unavailable,
and if its frontend id is missing the button is hidden. Both `.env` files are git-ignored — never
commit secrets.

### Endpoints

| Method | Path | Provider | Request body |
|---|---|---|---|
| POST | `/api/v1/auth/google` | Google | `{ "code": "<authorization code>" }` |
| POST | `/api/v1/auth/oauth/{provider}` | `feishu` \| `lark` | `{ "code": "<authorization code>" }` |
| GET  | `/api/v1/auth/me` | — | (Bearer access token) |

All return the standard envelope with `data` = `TokenPairDTO`
(`{ access_token, refresh_token, token_type, expires_in }`).

### Configuration

| Provider | Where to get credentials | Backend `.env` (`backend/.env`) | Frontend `.env` (`frontend/.env`) |
|---|---|---|---|
| **Google** | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → OAuth 2.0 **Web** client | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` (default `postmessage`) | `VITE_GOOGLE_CLIENT_ID` |
| **Feishu** | [飞书开放平台](https://open.feishu.cn/app) → self-built app → Credentials | `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_OAUTH_REDIRECT_URI` | `VITE_FEISHU_APP_ID` (optional: `VITE_FEISHU_AUTHORIZE_URL`, `VITE_FEISHU_REDIRECT_URI`) |
| **Lark** | [Lark Open Platform](https://open.larksuite.com/app) → self-built app → Credentials | `LARK_APP_ID`, `LARK_APP_SECRET`, `LARK_OAUTH_REDIRECT_URI` | `VITE_LARK_APP_ID` (optional: `VITE_LARK_AUTHORIZE_URL`, `VITE_LARK_REDIRECT_URI`) |

Notes:
- **Google** needs both `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`; Feishu/Lark each need both
  `*_APP_ID` and `*_APP_SECRET`. Missing either disables that provider (no button, fail-closed).
- **Redirect URI** — Feishu/Lark use a full-page redirect. The frontend default callback is
  `{origin}/auth/callback` (e.g. `http://localhost:5173/auth/callback`). Register **exactly this URL**
  in the provider console, and set the backend `*_OAUTH_REDIRECT_URI` to the same value. Google's popup
  flow uses the fixed `postmessage` redirect, so no callback URL registration is needed.
- **Scopes** — for Feishu/Lark request the contact/`user_info` scope. To enable email auto-linking,
  make sure the app can return `enterprise_email` (admin-assigned, treated as the verified email).
- The Feishu/Lark token (`/open-apis/authen/v2/oauth/token`) and user_info
  (`/open-apis/authen/v1/user_info`) hosts are selected automatically per provider; only the
  authorize URL is overridable from the frontend.

Example `backend/.env` (dev):

```bash
GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxx
FEISHU_APP_ID=cli_xxxx
FEISHU_APP_SECRET=xxxx
FEISHU_OAUTH_REDIRECT_URI=http://localhost:5173/auth/callback
LARK_APP_ID=cli_xxxx
LARK_APP_SECRET=xxxx
LARK_OAUTH_REDIRECT_URI=http://localhost:5173/auth/callback
```

Example `frontend/.env` (dev):

```bash
VITE_API_URL=http://localhost:8010
VITE_GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
VITE_FEISHU_APP_ID=cli_xxxx
VITE_LARK_APP_ID=cli_xxxx
```

### How it wires into the system

Request flow (Feishu/Lark redirect flow; Google uses a popup but the backend half is the same):

```
[Login page] click button
  → frontend builds authorize URL + random state (CSRF) → full-page redirect to provider
[Provider] user authorizes
  → redirect to {origin}/auth/callback?code=...&state=...
[/auth/callback] verify state → POST /api/v1/auth/oauth/{provider} { code }
[Backend] exchange code → trusted identity → find/link/create user → issue our JWT pair
  → frontend stores session → navigate to app
```

**Linking policy (find/link/create):** match on `(provider, provider_sub)` first; else auto-link to an
existing account only when the email is **verified** (Google `email_verified` / Feishu
`enterprise_email`); else create a new password-less user. When no verified email is available, a
placeholder `{provider_sub}@{provider}.local` is synthesized (no schema change). Details:
[`docs/project/api/auth.md`](docs/project/api/auth.md) and
[`docs/project/data/auth.md`](docs/project/data/auth.md).

Key files (extend a provider by touching these):

- Backend
  - `core/config.py` — provider env settings
  - `application/ports/oauth.py` — identity + exchanger ports (`OAuthIdentity`, `*AuthCodeExchanger`)
  - `infrastructure/external/google/`, `infrastructure/external/lark/` — provider adapters (code → identity)
  - `application/services/auth_service.py` — shared `_complete_oauth_login` + `login_with_google` / `login_with_oauth`
  - `api/routes/auth.py` — `/auth/google` and `/auth/oauth/{provider}` routes
  - `api/dependencies.py` — composition root (`_get_google_exchanger`, `_get_oauth_exchangers`)
- Frontend
  - `src/features/auth/helpers/oauthProviders.ts` — read enabled providers from env
  - `src/features/auth/helpers/oauthRedirect.ts` — build authorize URL + state
  - `src/features/auth/components/` — provider buttons + `OAuthCallbackScreen`
  - `src/routes/auth/callback.tsx` — `/auth/callback` route
  - `src/features/auth/api/authApi.ts` — `loginWithGoogle` / `loginWithOAuth`

To add another Feishu/Lark-family provider: add a `*_APP_ID/SECRET` config block, register its host in
`LARK_OPEN_HOSTS`, wire it into `_get_oauth_exchangers`, allow it in the `OAuthProvider` enum, and add a
`VITE_*_APP_ID` on the frontend.

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

- [Architecture](docs/project/architecture.md)
- [AI workflow](docs/reference/guides/ai-workflow.md)
- [FastAPI review checklist](docs/reference/guides/review-checklist-python-fastapi.md)
- [Auth API contract](docs/project/api/auth.md)
- [Auth data model](docs/project/data/auth.md)
