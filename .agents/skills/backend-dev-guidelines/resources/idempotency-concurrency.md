# Idempotency And Concurrency

Load this for retries, duplicate requests, idempotency keys, locks, concurrent updates, state transitions, or check-then-act logic.

## Risks

- Duplicate creates on client retry.
- Race between existence check and insert/update.
- Repeated side effects on retry.
- Lost update in state transitions.
- Lock without timeout or stale lock recovery.

## Idempotency

- Bind idempotency keys to a request hash, actor/scope, and operation.
- Return the same result for a completed duplicate request.
- Reject or wait on in-progress duplicates according to existing service behavior.
- Set TTLs intentionally and document them through settings when configurable.

## Concurrency

- Prefer database constraints for uniqueness.
- Use conditional updates, row locks, optimistic versioning, or unique indexes when concurrent requests can violate invariants.
- Do not rely only on pre-checks such as `exists_by_email` for uniqueness.
- State transitions should validate current state atomically when races matter.

## Tests

- Duplicate request with same key and same body.
- Same key with different body.
- Concurrent/duplicate create when unique constraints matter.
- Illegal repeated state transition when relevant.

## Completion Check

- Idempotency key scope is not global by accident.
- Request hash prevents replaying different payloads.
- DB constraints backstop uniqueness.
- Retry behavior does not duplicate irreversible side effects.
