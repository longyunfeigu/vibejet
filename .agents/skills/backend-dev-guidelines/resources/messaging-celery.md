# Messaging And Celery

Load this for Celery tasks, Kafka/messaging, background workers, retries, DLQ, async dispatch, or task scheduling.

## Boundaries

- Application should depend on a dispatcher/producer port when business code needs async work.
- Infrastructure owns Celery/Kafka clients, task declarations, serialization, retry/DLQ, and worker setup.
- Domain does not know about queues or workers.

## Message Design

- Messages should contain stable identifiers and minimal payloads.
- Consumers should reload authoritative state when needed.
- Include idempotency/correlation identifiers.
- Version message schemas when consumers can outlive producers.

## Retry Safety

- Assume tasks may run more than once.
- Make handlers idempotent or guard side effects.
- Distinguish retryable provider failure from permanent validation/business failure.
- Use DLQ or failure state when retries exhaust.

## Async In Celery

- Celery task functions are sync wrappers around async application code when needed.
- Manage event loops and DB sessions using existing infrastructure patterns.
- Close/dispose resources when worker lifecycle requires it.

## Tests

- Unit test task handler/application service with fake ports.
- Test retry/error mapping for critical tasks.
- Test idempotency for side-effecting consumers.

## Completion Check

- Message emission order vs DB commit is intentional.
- Consumer is idempotent.
- Failures are observable and retry policy is explicit.
- Payload does not expose secrets or excessive data.
