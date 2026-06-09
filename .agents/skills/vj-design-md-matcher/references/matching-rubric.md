# DESIGN.md Matching Rubric

Use this rubric after running `scripts/match_design_md.py`. The script is a retrieval aid; final selection must still be judged against the PRD.

## Score Dimensions

Use a 0-5 score for each dimension.

| Dimension | Meaning | 5 means |
| --- | --- | --- |
| Domain fit | Similar user expectations, market, and trust model | The reference's product category maps naturally to the PRD |
| Workflow fit | Similar user tasks and interaction loops | It supports the same CRUD, review, creation, dashboard, or reading patterns |
| Density fit | Similar amount of information per screen | It handles the PRD's tables, filters, forms, metadata, and state density |
| Tone fit | Similar emotional posture | It matches the desired utilitarian, premium, friendly, technical, or editorial tone |
| Practicality | Easy to implement in the target app | Tokens and layout rules can be applied without special assets or brand-specific effects |

Recommended references should score at least 17/25 unless there is a clear reason to include a contrast reference.

## Selection Heuristics

For SaaS/admin/business systems:

- Prefer references with clear navigation, tables, status surfaces, forms, and restrained visual rhythm.
- Strong candidates often come from Productivity & SaaS, Developer Tools, Backend/DevOps, Design & Creative Tools, or documentation products.
- Avoid consumer retail, automotive, media, gaming, and highly cinematic systems unless the PRD is brand/marketing-heavy.

For content, knowledge, docs, or training products:

- Prefer references with readable content hierarchy, editor or knowledge-base patterns, and calm navigation.
- Combine one content-oriented reference with one operational/admin reference when the product includes management workflows.

For fintech or high-trust workflows:

- Prefer references that communicate accuracy, auditability, and clear state changes.
- Avoid playful or heavily decorative systems unless the PRD explicitly asks for it.

For AI/developer tools:

- Prefer references that handle technical concepts, code snippets, job/status feedback, and dense configuration.
- Avoid pure landing-page aesthetics if the target is an internal tool.

## Anti-Copying Rules

Do not copy:

- brand-specific colors as-is when they are recognizable
- proprietary typeface names as requirements
- logos, marks, product illustrations, or photography direction
- exact component styling that would make the project look like the reference brand

Do borrow:

- token structure
- density strategy
- navigation rhythm
- table/form/review patterns
- state hierarchy
- accessibility discipline
- restraint level

## Recommendation Format

Use this format before writing the project DESIGN.md:

```markdown
## Recommended References

1. Reference Name
   - Fit: ...
   - Borrow: ...
   - Avoid: ...
   - Source: ...

2. Reference Name
   - Fit: ...
   - Borrow: ...
   - Avoid: ...
   - Source: ...

3. Reference Name
   - Fit: ...
   - Borrow: ...
   - Avoid: ...
   - Source: ...
```

Then ask for confirmation unless the user explicitly authorized direct generation.
