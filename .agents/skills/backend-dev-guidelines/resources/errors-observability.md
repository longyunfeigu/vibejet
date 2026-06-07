# Errors And Observability

Use this for exception handling, response envelopes, logging, metrics, tracing, and middleware error flow.

## Error Contract

- `domain.common.exceptions.BusinessException` is the expected business-error base.
- `DomainValidationException` represents invalid domain state/input.
- `core.exceptions.register_exception_handlers` maps business codes and validation errors to HTTP responses.
- `core.response.Response[T]`, `ErrorDetail`, `success_response`, `error_response`, and `paginated_response` define the API envelope.

## Sentry / Error Reporting

- Do not report every expected 4xx business error to Sentry.
- Report unexpected exceptions, external system failures, task failures, data consistency failures, and retry exhaustion.
- Add context, but do not log secrets, tokens, raw credentials, or sensitive file contents.

## Logging

- Use `core.logging_config.get_logger(__name__)`.
- Do not use `print`.
- Include actionable context: request id, actor id when safe, resource id, provider, operation, idempotency key hash, correlation id.
- Do not log full JWTs, API keys, passwords, presigned URLs, large prompts, or full LLM/file payloads.

## Metrics / Tracing

- Add metrics or traces for new reusable platform capabilities, external dependencies, background processing, or high-volume critical paths.
- Health checks should cover new required external dependencies when startup/runtime behavior depends on them.

## Middleware / Exception Flow

- Keep request id and logging middleware aligned with existing `backend/api/middleware/` patterns.
- Global exception handlers should produce the standard response envelope for business APIs.
- Debug-only details must not leak in production.

## Completion Check

- Expected business failures use business/domain exceptions.
- Logs are structured and safe.
- Unexpected failures remain observable.
- Response shape matches `docs/project/api/conventions.md`.
