# Permissions

Load this for auth, roles, ownership, tenant boundaries, protected/public endpoints, or resource visibility.

## Default

New business endpoints are default-deny. They need authentication unless the task explicitly defines the endpoint as public.

## Where Checks Belong

- Route/dependency layer: authenticate actor and enforce simple role gates.
- Application service: ownership, tenant/resource boundary, workflow permission, data-dependent authorization.
- Domain: permission-independent invariants such as illegal state transitions.
- Repository: enforce query filters needed to avoid leaking records, but do not make repository the only place where business authorization exists.

## Required Checks

- Missing/invalid token -> 401.
- Authenticated but not allowed -> 403.
- Ownership mismatch -> 403 without leaking resource data.
- List endpoints must not return global data by accident.
- Detail/update/delete endpoints must filter or check owner/tenant/role.

## Public Endpoint Rules

Public endpoints must be explicit in code or docs. Do not infer public access from missing auth on old endpoints unless the task says to preserve legacy behavior.

## Tests

For protected routes, add/maintain tests for:

- unauthenticated request
- wrong role or wrong owner when relevant
- successful authorized request

## Completion Check

- Every new business route is protected or explicitly public.
- Application service receives enough actor context for ownership decisions.
- Repositories include owner/tenant filters where list/detail queries require them.
- API docs reflect auth expectations when contract changes.
