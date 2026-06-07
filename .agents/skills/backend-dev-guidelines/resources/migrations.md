# Migrations And Persistent Schema

Load this for ORM model changes, Alembic migrations, indexes, constraints, columns, tables, or persistent data-shape changes.

## Required Pairing

Schema work is not complete unless these are considered together:

- ORM model update under `backend/infrastructure/models/`
- Alembic migration under `backend/alembic/versions/`
- Repository/query changes
- Domain/application DTO changes when exposed
- Docs under `docs/project/data/` when the stable data model changes
- Tests for persistence/query behavior

## Migration Quality

- Use explicit names for constraints and indexes when project style supports it.
- Make nullable/default/backfill choices intentional.
- Avoid destructive migrations without a clear rollout and backup plan.
- Add unique constraints for business uniqueness; do not rely only on application checks.
- Add indexes for new high-cardinality filters/orderings used by endpoints.

## API Impact

If schema changes expose new public fields, remove fields, or change semantics, also update `docs/project/api/`.

## Verification

Run, when feasible:

```bash
cd backend
alembic upgrade head
pytest tests/ -q
```

If the environment cannot run migrations, inspect the migration and report that it was not executed.

## Completion Check

- Migration and model match.
- Downgrade is reasonable if the repo expects downgrade support.
- Data docs are updated for stable schema changes.
- Tests cover new constraints/defaults/query paths.
