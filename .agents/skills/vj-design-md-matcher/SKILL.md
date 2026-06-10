---
name: vj-design-md-matcher
description: Match a product PRD or product brief to three reference DESIGN.md files from the vibeui / VoltAgent awesome-design-md library using a bundled local cache first and network fallback only when needed, then synthesize a project-owned docs/project/DESIGN.md. Use when the user asks for automatic DESIGN.md library matching, vibeui style references, awesome-design-md recommendations, design-system inspiration before UI mockups, offline/local DESIGN.md matching, or wants to generate a stable project design direction from a PRD. This skill must run before implementation; do not use it inside vj-work execution to pick styles ad hoc.
---

# vj-design-md-matcher

根据 PRD 从 `vibeui / awesome-design-md` 设计库推荐 3 个参考 `DESIGN.md`，再生成项目自己的 `docs/project/DESIGN.md`。

## Boundary

This skill is a pre-design step:

```text
PRD -> vj-design-md-matcher -> docs/project/DESIGN.md -> vj-ui-mock / frontend implementation
```

Do not use this skill during `vj-work` or story implementation to choose a temporary visual style. Once `docs/project/DESIGN.md` exists and is confirmed, downstream work consumes that file as the stable style source.

Do not copy a brand's DESIGN.md into the project. Treat library entries as references for interaction density, layout rhythm, token discipline, and tone. Generate a project-owned system that fits the PRD.

## Inputs

Prefer inputs in this order:

1. User-specified PRD or brief path.
2. `docs/project/requirements.md`.
3. User's product description in the current conversation.

Optional inputs:

- local library mirror: path to `awesome-design-md` repo root or its `design-md/` directory.
- output path override: defaults to `docs/project/DESIGN.md`.
- explicit constraints: "avoid dark UI", "enterprise admin", "mobile first", "do not use gradients".

## Local Cache Policy

Prefer the bundled cache at `assets/awesome-design-md/` for all matching. This keeps the skill usable if `vibeui.top` becomes unavailable.

The authoritative cache source is `https://vibeui.top/site-assets/designs.js`, not only the GitHub `VoltAgent/awesome-design-md/design-md` directory. The vibeui catalog currently includes brand `design-md/*` entries plus `extra/uiuxskillProMax/generated/*/DESIGN.md` style templates, so it can contain more entries than the GitHub `design-md` directory alone.

Default behavior:

1. If `assets/awesome-design-md/design-md/*/DESIGN.md` exists, use it first.
2. If local cache misses entries and network is allowed, merge missing entries from `vibeui.top`.
3. If no cache exists, fall back to `vibeui.top`.
4. If `--offline` is set, fail instead of using network.

Refresh the cache when the catalog changes:

```bash
python3 .agents/skills/vj-design-md-matcher/scripts/match_design_md.py --download-cache
```

Use a custom cache location:

```bash
python3 .agents/skills/vj-design-md-matcher/scripts/match_design_md.py \
  --download-cache \
  --cache /path/to/design-md-cache
```

## Workflow

### Phase 1: Extract Product Signals

Read the PRD or product brief and summarize:

- domain and adjacent market
- target users and roles
- primary workflows
- page types: dashboard, table, editor, form, wizard, review queue, content page, marketing page
- information density: sparse, medium, high
- interaction intensity: read-only, CRUD, review/approval, real-time, creation tool
- desired tone: utilitarian, premium, friendly, editorial, technical, consumer, playful
- explicit visual constraints and anti-goals

If these signals are too vague, ask one concise clarification before matching.

### Phase 2: Retrieve Candidate DESIGN.md Entries

Use `scripts/match_design_md.py` for first-pass retrieval.

Default local-cache-first matching:

```bash
python3 .agents/skills/vj-design-md-matcher/scripts/match_design_md.py \
  --prd docs/project/requirements.md \
  --limit 8
```

Local mirror:

```bash
python3 .agents/skills/vj-design-md-matcher/scripts/match_design_md.py \
  --prd docs/project/requirements.md \
  --local /path/to/awesome-design-md \
  --limit 8
```

Offline local-only:

```bash
python3 .agents/skills/vj-design-md-matcher/scripts/match_design_md.py \
  --prd docs/project/requirements.md \
  --offline \
  --limit 8
```

Conversation-only brief:

```bash
python3 .agents/skills/vj-design-md-matcher/scripts/match_design_md.py \
  --query "enterprise employee exam and grading admin system, high-density tables, review workflow" \
  --limit 8
```

The script returns candidate names, categories, links, descriptions, source mode, and score breakdowns. It uses the bundled cache first and `vibeui.top/site-assets/designs.js` as the network source. `--source github` is available only as a legacy fallback for the smaller `VoltAgent/awesome-design-md/design-md` source.

### Phase 3: Score and Recommend Three

Read `references/matching-rubric.md` before final selection.

Select exactly 3 references:

- primary reference: closest product/workflow fit
- secondary reference: complementary interaction or layout pattern
- contrast reference: useful constraint or anti-pattern boundary

For each selected reference, report:

- why it fits the PRD
- which parts to borrow
- which parts to avoid
- source link to its `DESIGN.md`

If the top script results are visually unsafe for the project, override them and explain why.

### Phase 4: User Confirmation

Before writing `docs/project/DESIGN.md`, show the 3-reference recommendation and wait for user confirmation unless the user explicitly asked to proceed without review.

If the user rejects one reference, replace only that reference and keep the rest stable.

### Phase 5: Generate Project DESIGN.md

Write `docs/project/DESIGN.md` with these sections:

```markdown
# DESIGN.md

## Product Design Direction
## Reference Inspirations
## Visual Principles
## Color Tokens
## Typography Tokens
## Layout Rules
## Spacing Hierarchy
## Component Rules
## Interaction States
## Data-Dense UI Rules
## Richness Floor by Screen-Type
## Reference Skeletons (per screen archetype)
## Accessibility Rules
## Do / Don't
## Downstream Prompt Base
```

Rules for generation:

- Make the system fit the product, not the reference brands.
- Use practical tokens that a frontend engineer can implement.
- Keep palettes balanced; avoid one-note purple/blue gradients, decorative orbs, heavy beige themes, or brand-copy colors unless the PRD demands them.
- For SaaS/admin tools, default **operational** screens (tables, queues, editors) to quiet, dense, scannable composition. BUT do **not** blanket-apply this austerity to **front-of-house** screens (login, first-run, landing, empty-first-screen): those must meet a **richness floor** — intentional composition + product identity within the *same* tokens — never marketing gradient/orb/glass. A token system that is "correct" but produces a lone centered card on every screen has failed; encode the floor explicitly so downstream executors don't ship AC-minimal screens.
- `Spacing Hierarchy` is **mandatory** and must be layered, not a single range. A flat rule like "operational screens use 8–16" will be executed literally by downstream AI as wall-to-wall 8px and the result reads as Excel, not as Linear. Always specify per-level hard ranges: page frame (content padding, around the page header) > region gaps (between header / stats / toolbar / table) > container internal padding > component rhythm > row height. State the principle explicitly: **density lives in the data core; air lives at the page frame** — premium dense references (Linear, Airtable) pack rows but keep generous page padding. Include machine-checkable floors (minimum page padding, minimum region gap, max ~4 distinct gap values per screen) so the exit gate can measure screenshots against them.
- `Richness Floor by Screen-Type`: for each screen archetype present in the PRD (front-of-house / dashboard / table-list / detail-reading / form-wizard), state a one-line **floor** (the minimum intentional composition, not an upper bound). Make clear richness = deliberate composition + identity + hierarchy, not decoration.
- `Reference Skeletons (per screen archetype)`: **do not discard the matched references' composition after extracting tokens.** Distill each selected reference's *structure and density* into a concrete per-archetype skeleton (regions, order, density), re-skinned with this file's tokens — so the executor copies a good skeleton instead of inventing a minimal one. Include a project-specific skeleton for the product's primary login/auth screen when the PRD has one.
- Include states for loading, empty, error, disabled, selected, dirty, saved, review-needed, and destructive actions when relevant.
- The `Downstream Prompt Base` must be reusable by `vj-ui-mock` or frontend work and must explicitly say to follow this `DESIGN.md`.

## Outputs

- Recommendation summary in chat.
- `docs/project/DESIGN.md` after confirmation or explicit proceed.
- Optional retrieval JSON when requested:

```bash
python3 .agents/skills/vj-design-md-matcher/scripts/match_design_md.py \
  --prd docs/project/requirements.md \
  --json > /tmp/design-md-candidates.json
```

## Relationship To Other Skills

- `vj-product-requirements`: upstream PRD source.
- `vj-ui-mock`: downstream; it should consume `docs/project/DESIGN.md` as the stable design direction.
- `design-taste-frontend` / `frontend-dev-guidelines`: implementation-time quality guardrails, not library matching.
- `vj-work`: do not integrate this skill into execution; execution should not pick new styles.
