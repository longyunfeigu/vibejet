# PRD Quality Rubric

Use this rubric for `review` mode and Phase 4 in `create` / `update` modes.

Score the PRD out of 100. A PRD below 75 must not proceed to `vj-architecture`. Fix or clarify the blocking areas first.

## Gate Rules

- `>= 85`: Ready for `vj-architecture`.
- `75-84`: Conditionally ready only if no critical blockers remain; list follow-up risks.
- `< 75`: Not ready for `vj-architecture`; return to clarification or rewrite.

Critical blockers override the score. If any critical blocker exists, the PRD is not ready even if the score is 75 or higher.

Critical blockers:
- No clear target user or role definitions.
- No concrete user problem or counterfactual workaround.
- Functional requirements are not testable.
- Major requirements are unlabeled or indistinguishable between user input, research, and inference.
- Non-goals are missing for a broad or ambiguous product.
- Architecture Handoff is empty when the product has security, compliance, data, integration, scale, or reliability constraints.
- Epic Decomposition Notes are missing when downstream Story generation is expected.

## Scoring

### 1. Problem, User, and Evidence: 15

| Points | Criteria |
|--------|----------|
| 0-5 | User, problem, or usage context is vague. |
| 6-10 | User and problem are named, but evidence, frequency, or current workaround is weak. |
| 11-15 | Target users, scenarios, current workaround, evidence, and success outcomes are concrete. |

### 2. Scope and Non-Goals: 15

| Points | Criteria |
|--------|----------|
| 0-5 | Scope is open-ended; non-goals are absent or generic. |
| 6-10 | Scope is mostly clear, but MVP/deferred boundaries need sharpening. |
| 11-15 | MVP, deferred capabilities, explicit exclusions, and scope mode are clear. |

### 3. Functional Requirements Quality: 20

| Points | Criteria |
|--------|----------|
| 0-7 | Requirements are vague, solution-biased, or not testable. |
| 8-14 | Most requirements are testable, but some lack actors, triggers, or outcomes. |
| 15-20 | EARS requirements have clear actors, triggers, outcomes, sources, and acceptance-ready behavior. |

### 4. Epic Structure: 10

| Points | Criteria |
|--------|----------|
| 0-3 | Epics are grouped by pages, components, or technical layers. |
| 4-7 | Epics are mostly user-value oriented but have unclear boundaries or overlap. |
| 8-10 | Epics are organized by user goals or business capabilities and can be decomposed into Stories. |

### 5. Non-Functional Requirements and Constraints: 10

| Points | Criteria |
|--------|----------|
| 0-3 | NFRs are missing or generic. |
| 4-7 | Relevant NFRs are present but not measurable or tied to product risk. |
| 8-10 | Performance, usability, security, compliance, reliability, and operational constraints are specific where relevant. |

### 6. Traceability, Assumptions, and Evidence: 10

| Points | Criteria |
|--------|----------|
| 0-3 | Sources and assumptions are unclear. |
| 4-7 | Sources are labeled, but inferred requirements or validation tasks are incomplete. |
| 8-10 | User input, research, inference, assumptions, dependencies, and validation tasks are clearly separated. |

### 7. Architecture Handoff: 10

| Points | Criteria |
|--------|----------|
| 0-3 | Handoff is absent, technical-solution-heavy, or repeats the PRD. |
| 4-7 | Handoff lists some constraints but misses data, permission, dependency, or open-question impact. |
| 8-10 | Handoff clearly captures product constraints, external dependencies, data/permission boundaries, and architecture-impacting open questions. |

### 8. Epic Decomposition Notes: 5

| Points | Criteria |
|--------|----------|
| 0-1 | Notes are absent or technical-task oriented. |
| 2-3 | Notes provide some ordering or dependency guidance. |
| 4-5 | Notes define MVP order, dependencies, non-splittable user capabilities, deferred scope, and Story acceptance focus. |

### 9. Internal Consistency and Readiness: 5

| Points | Criteria |
|--------|----------|
| 0-1 | Contradictions, placeholders, or unresolved ambiguity remain. |
| 2-3 | Minor inconsistencies or weak wording remain. |
| 4-5 | No material contradictions, placeholders, ambiguous terms, or unsupported downstream assumptions. |

## Review Output Format

```text
## PRD Quality Review

Score: X/100
Gate: Ready / Conditionally Ready / Not Ready

### Critical Blockers
- ...

### Findings
- [Severity] [Section] Issue -> Suggested fix

### Missing Decisions
- ...

### Handoff Readiness
- Architecture: Ready / Not Ready, because ...
- Epic Decomposition: Ready / Not Ready, because ...

### Suggested Edits
- ...
```

## Phase 4 Mechanical Checks

Run these before scoring:
- Search for placeholders: `TBD`, `TODO`, `[填写]`, `<待定>`, `未定`.
- Check that source labels are used consistently: `[用户]`, `[调研]`, `[推断]`.
- Check that stated non-goals are not contradicted by requirements.
- Check that EARS requirements do not use vague words such as "friendly", "fast", "smart", or "easy" without a measurable definition.
- Check that Architecture Handoff avoids implementation decisions such as database tables, API paths, framework choices, or deployment topology.
- Check that Epic Decomposition Notes do not split work by frontend/backend/database layers.
