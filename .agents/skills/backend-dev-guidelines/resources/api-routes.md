# API Routes

Use this for `backend/api/routes/`, `backend/api/dependencies.py`, route registration, and HTTP-facing behavior.

## Responsibilities

- Define path, method, tags, summary, query/path/body params, dependencies, and `response_model`.
- Delegate use cases to `application` services.
- Format successful responses with `success_response` or `paginated_response`.
- Let global handlers convert `BusinessException`, `DomainValidationException`, validation errors, and HTTP auth errors to the standard envelope.

## Must Not

- Do not directly import ORM models, SQLAlchemy sessions, concrete repositories, or infrastructure clients except through dependency factories/adapters already used by the repo.
- Do not write business invariants in routes.
- Do not create a controller layer by default.
- Do not return raw dicts from business endpoints unless the existing endpoint is explicitly operational/non-business.
- Do not hand-build `{code, message, data, error}`.

## Response Contract

- Business endpoint: `response_model=ApiResponse[T]`.
- List endpoint: use `ApiResponse[PaginatedData[T]]` when returning page/size/total.
- Use `settings.DEFAULT_PAGE_SIZE` and `settings.MAX_PAGE_SIZE` for standard pagination when applicable.
- Operational endpoint: raw JSON is allowed only for health, metrics, root, or explicit operational APIs.

## Auth

- New business endpoints are protected by default.
- Public endpoints must be visibly intentional in code or task docs.
- Use `get_current_user` for authenticated actor and `require_role(*roles)` for role gates when available.
- Ownership checks belong in `application` services when they require resource data.

## Error Translation

- Prefer raising application/domain exceptions and letting `core.exceptions.register_exception_handlers` format responses.
- Use `HTTPException` only for transport/auth adapter behavior or existing patterns. It still flows through the global HTTP exception handler.
- Do not catch broad exceptions in routes unless adding context and re-raising.

## Completion Check

- Route is thin and delegates to an application service.
- `response_model` matches the envelope.
- Endpoint is explicitly protected or explicitly public.
- No direct repository/session/model access appears in the route.
- API docs under `docs/project/api/` are updated if the public contract changed.
