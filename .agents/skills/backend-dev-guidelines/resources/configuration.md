# Configuration

Use this for `backend/core/config.py`, settings models, environment parsing, and runtime configuration.

## Responsibilities

- Centralize runtime configuration in `core.config.settings`.
- Use `pydantic-settings` and typed settings models.
- Keep secrets out of code, logs, docs examples, and tests.
- Validate required runtime settings early enough that misconfiguration fails clearly.

## Must Not

- Do not scatter raw `os.getenv` calls across application, domain, API routes, repositories, or clients.
- Do not make domain behavior depend on environment variables.
- Do not add production defaults that silently weaken security.
- Do not log full connection strings, API keys, JWT secrets, or provider credentials.

## Environment Shape

- Preserve existing nested env naming such as `DATABASE__URL`, `REDIS__URL`, and provider-specific nested settings.
- Keep `.env.example` / `env.example` aligned when adding required public configuration keys.
- If a setting affects public API behavior, document the behavior under `docs/project/api/` when stable.

## Tests

- Add/update config tests for required settings, defaults, parsing, and validation failures.
- Prefer isolated settings construction over mutating global process env in a way that leaks across tests.

## Completion Check

- New config is typed and centralized.
- Required secrets fail fast when absent.
- Examples are safe and non-secret.
- Tests cover parsing or validation for nontrivial settings.

