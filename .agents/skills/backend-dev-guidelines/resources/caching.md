# Caching

Load this for Redis, cache keys, TTL, invalidation, distributed locks, or cache-backed idempotency.

## Source Of Truth

Cache is not the source of truth unless the feature is explicitly a cache/lock/idempotency store. Persistent business state belongs in the database or external authoritative system.

## Key Design

- Include namespace, entity, id/scope, version when needed.
- Include actor/tenant scope for permission-sensitive data.
- Do not cache data that can leak across users.
- Use stable serialization.

## TTL And Invalidation

- TTL must match staleness tolerance.
- Invalidate on writes when stale reads are not acceptable.
- Cache null/negative results only with short TTL and clear intent.
- Avoid unbounded key growth.

## Distributed Locks

- Use locks with timeout and unique token/owner when supported.
- Always release in `finally` or context manager.
- Treat lock acquisition failure as an expected path.
- Do not use a cache lock as the only guard for critical uniqueness; backstop with DB constraints when possible.

## Tests

- Cache miss -> source load -> set.
- Cache hit -> no source load.
- Invalidation/write path.
- Lock contention when lock correctness matters.

## Completion Check

- Key includes the right scope.
- TTL and invalidation are explicit.
- Sensitive data cannot leak cross-actor.
- DB/source-of-truth consistency is understood.
