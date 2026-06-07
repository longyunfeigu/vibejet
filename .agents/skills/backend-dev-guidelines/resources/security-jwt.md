# Security And JWT

Use this for JWT helpers, token signing/parsing, password hashing, auth security utilities, and files under `backend/infrastructure/security/`.

## Responsibilities

- Keep cryptographic and token primitives small, explicit, and covered by tests.
- Keep business authorization decisions outside token helper code; helpers sign, verify, parse, and return stable claims/errors.
- Use typed settings from `core.config.settings` for secrets, algorithms, issuer/audience, TTL, and related security configuration.
- Keep token behavior aligned with `docs/project/api/` and task acceptance criteria.

## Must Not

- Do not hard-code secrets, algorithms, or test credentials in implementation code.
- Do not log full JWTs, bearer headers, signing keys, passwords, password hashes, or credential-bearing URLs.
- Do not trust unverified token claims.
- Do not let infrastructure security helpers import `api` routes or make HTTP response decisions.
- Do not silently accept malformed, missing, expired, wrong-algorithm, or wrong-subject tokens.

## JWT Claims

- Keep required claims explicit. For this repo's MVP identity flow, `sub=user_id` is the stable subject unless the API contract changes.
- Validate required claims before loading the actor.
- Map invalid/missing/tampered tokens to `UNAUTHORIZED` / 401 through existing exception handling.
- If `exp`, issuer, audience, or rotation is introduced, update `docs/project/api/` and tests.

## Passwords And Secrets

- Use established hashing libraries and constant-time comparisons where password verification exists.
- Keep secret-key validation centralized in settings.
- Test secret/config missing cases when behavior is nontrivial.

## Tests

- Sign and verify a valid token.
- Missing token, malformed token, tampered token, and wrong/missing required claim.
- Config/secret validation if settings are added or changed.
- No API route or ORM dependency leaks into security helper tests.

## Completion Check

- Token helper is isolated from HTTP response formatting.
- Claims and settings match API docs and acceptance criteria.
- Unsafe token/secret logging is absent.
- Auth dependencies/application services own actor loading and permission semantics.
