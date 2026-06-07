# Transactions And Side Effects

Load this when a DB write is combined with storage, HTTP, SDK, queue, email, LLM, Celery, Kafka, cache invalidation, or any irreversible side effect.

## Main Risk

DB state and external side effects can diverge. Decide what happens when either side succeeds and the other fails.

## Preferred Patterns

- Persist intent/state first, commit, then dispatch async side effect when eventual consistency is acceptable.
- Use outbox/retry/reconciliation for durable cross-system workflows.
- Make external operations idempotent where possible.
- For storage delete/update, decide whether failure is blocking, retryable, or reconciled later.

## Avoid

- Calling a non-idempotent external API inside an open transaction without compensation.
- Returning success after swallowing side-effect failure unless the degraded behavior is intentional and logged.
- Updating cache as the source of truth.
- Emitting messages before the DB commit if consumers assume committed data exists.

## Questions To Answer In Code Or Plan

- What is the source of truth?
- Can the external action be retried safely?
- If DB commit succeeds and side effect fails, what observes and repairs it?
- If side effect succeeds and DB rolls back, what compensates or prevents duplication?
- Is user response synchronous success, accepted/pending, or failure?

## Completion Check

- Transaction boundary is explicit.
- Side-effect ordering is intentional.
- Failure path is logged/observable.
- Tests cover at least one side-effect failure or duplicate/retry path when feasible.
