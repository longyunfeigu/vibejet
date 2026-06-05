# YAML Frontmatter Schema

`schema.yaml` in this directory is the canonical contract for `docs/solutions/` frontmatter written by `vj-compound` and read by the `vj-learnings-researcher` agent.

Use this file as the quick reference for required fields, enum values, validation expectations, category mapping, and track classification (bug vs knowledge).

## Tracks

The `problem_type` determines which **track** applies. Each track has different required and optional fields.

| Track | problem_types | Description |
|-------|--------------|-------------|
| **Bug** | `build_error`, `test_failure`, `runtime_error`, `performance_issue`, `database_issue`, `security_issue`, `ui_bug`, `integration_issue`, `logic_error` | Defects and failures that were diagnosed and fixed |
| **Knowledge** | `best_practice`, `documentation_gap`, `workflow_issue`, `developer_experience`, `architecture_pattern`, `design_pattern`, `tooling_decision`, `convention` | Practices, patterns, conventions, decisions, workflow improvements, and documentation. Prefer the narrowest applicable value; `best_practice` is the fallback. |

## Required Fields (both tracks)

- **module**: Module or area affected (e.g. `conversation`, `file_asset`, `material`, `exam`, `attempt`, `auth`)
- **date**: ISO date in `YYYY-MM-DD`
- **problem_type**: One of the values in the Tracks table above
- **component**: One of `domain_entity`, `domain_service`, `repository`, `application_service`, `port_adapter`, `api_route`, `middleware`, `infrastructure_external`, `celery_task`, `database`, `migration`, `llm_integration`, `idempotency`, `auth`, `config`, `frontend_feature`, `frontend_route`, `frontend_component`, `testing`, `documentation`, `tooling`, `development_workflow`
- **severity**: One of `critical`, `high`, `medium`, `low`

## Bug Track Fields

Required:
- **symptoms**: YAML array with 1-5 observable symptoms (errors, broken behavior)
- **root_cause**: One of `missing_association`, `missing_include`, `missing_index`, `wrong_api`, `scope_issue`, `thread_violation`, `async_timing`, `memory_leak`, `config_error`, `logic_error`, `test_isolation`, `missing_validation`, `missing_permission`, `missing_workflow_step`, `inadequate_documentation`, `missing_tooling`, `incomplete_setup`
- **resolution_type**: One of `code_fix`, `migration`, `config_change`, `test_fix`, `dependency_update`, `environment_setup`, `workflow_improvement`, `documentation_update`, `tooling_addition`, `seed_data_update`

## Knowledge Track Fields

No additional required fields beyond the shared ones. All optional: **applies_when**, **symptoms**, **root_cause**, **resolution_type**.

## Optional Fields (both tracks)

- **related_components**: Other components involved
- **tags**: Search keywords, lowercase and hyphen-separated

## Category Mapping (problem_type → docs/solutions/ subdirectory)

- `build_error` -> `build-errors/`
- `test_failure` -> `test-failures/`
- `runtime_error` -> `runtime-errors/`
- `performance_issue` -> `performance-issues/`
- `database_issue` -> `database-issues/`
- `security_issue` -> `security-issues/`
- `ui_bug` -> `ui-bugs/`
- `integration_issue` -> `integration-issues/`
- `logic_error` -> `logic-errors/`
- `developer_experience` -> `developer-experience/`
- `workflow_issue` -> `workflow-issues/`
- `best_practice` -> `best-practices/`
- `documentation_gap` -> `documentation-gaps/`
- `architecture_pattern` -> `architecture-patterns/`
- `design_pattern` -> `design-patterns/`
- `tooling_decision` -> `tooling-decisions/`
- `convention` -> `conventions/`

All paths are under `docs/solutions/`. Create the subdirectory if it does not exist.

## Validation Rules

1. Determine the track from `problem_type` using the Tracks table.
2. All shared required fields must be present.
3. Bug-track required fields (`symptoms`, `root_cause`, `resolution_type`) must be present on bug-track docs.
4. Knowledge-track docs have no additional required fields beyond the shared ones.
5. Enum fields must match the allowed values exactly.
6. Array fields must respect min/max item counts.
7. `date` must match `YYYY-MM-DD`.

## YAML Safety Rules

Strict YAML 1.2 parsers (`yq`, `js-yaml` strict, PyYAML) reject array items that start with a reserved indicator character as unquoted scalars. When writing items for any array-of-strings field (`symptoms`, `applies_when`, `tags`, `related_components`), wrap the value in double quotes if it starts with any of:

`` ` ``, `[`, `*`, `&`, `!`, `|`, `>`, `%`, `@`, `?`

Also quote if the value contains the substring `": "`.

Example — before (breaks strict YAML):

    symptoms:
      - `alembic upgrade head` silently no-ops when versions/ is empty

Example — after (parses cleanly):

    symptoms:
      - "`alembic upgrade head` silently no-ops when versions/ is empty"

Run `scripts/validate-frontmatter.py <doc-path>` after writing to catch silent-corruption quoting issues.
