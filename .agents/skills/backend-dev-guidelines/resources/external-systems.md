# External Systems

Load this for HTTP clients, SDKs, storage providers, LLM providers, email, payment, object storage, or any service outside the process.

## Boundaries

- Application depends on a port under `backend/application/ports/`.
- Infrastructure implements the port with concrete SDK/client code.
- API routes do not instantiate external clients directly.
- Domain never calls external systems.

## Reliability

- Configure timeouts.
- Decide retry policy based on operation idempotency.
- Add circuit/degraded behavior only when product behavior is clear.
- Surface provider errors as business/service exceptions when clients need stable semantics.
- Log provider, operation, correlation id/request id, and safe error details.

## Configuration

- Use `core.config.settings`.
- Do not scatter raw `os.getenv`.
- Validate required settings at startup or dependency construction.
- Never commit or log secrets.

## Tests

- Use fake ports for application tests.
- Mock SDK/HTTP clients for infrastructure tests.
- Cover timeout/error mapping for critical integrations.

## Completion Check

- Port exists or existing port is reused.
- Concrete client is isolated in infrastructure.
- Timeouts/retries are intentional.
- No secrets or raw payloads in logs.
