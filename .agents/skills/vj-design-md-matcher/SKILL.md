---
name: vj-design-md-matcher
description: Match a product-level UI/brand brief or PRD to three reference DESIGN.md files from the vibeui / VoltAgent awesome-design-md library using a bundled local cache first and network fallback only when needed, then synthesize a project-owned docs/project/DESIGN.md and golden screen references. Use when a project lacks DESIGN.md, brand/product visual direction is unclear, front-of-house/golden screens are missing, the user asks for automatic DESIGN.md library matching, vibeui style references, awesome-design-md recommendations, or a stable project design direction. This is a low-frequency product/brand direction step before implementation; do not use it inside vj-work execution or for routine single-screen structure/state work.
---

# vj-design-md-matcher

From a product-level UI/brand brief or PRD, recommend 3 reference `DESIGN.md` files from the
vibeui / awesome-design-md library, then write the project's own `docs/project/DESIGN.md` and
golden screen references.

This is the low-frequency product/brand direction step. Once `DESIGN.md` exists and is confirmed,
downstream work (`vj-plan`, `vj-work`) consumes it; do not run this skill
during execution to pick a temporary style. Single-screen structure and states belong to
`ui-page-goal-structure` / `ui-state-coverage`, not here.

Run it only when: `DESIGN.md` is missing or explicitly obsolete; product/brand direction is
unclear; a front-of-house screen (login, signup, landing, onboarding, first-run empty state) has
no golden reference; a new downstream product needs its own system; or the user asks for this
matching or a DESIGN.md rewrite.

Do not copy a brand's DESIGN.md. Borrow interaction density, layout rhythm, token discipline and
tone; generate a system that fits this PRD.

## Inputs

In order of preference: a product-level brief (ideally from `ui-requirement-brief`), a PRD or
brief path the user names, `docs/product/requirements.md`, the conversation. Optional: a local
library mirror, an output path, explicit constraints ("avoid dark UI", "mobile first"). Single-screen
briefs are examples of key archetypes, not the product identity.

## Phase 1: Extract product signals

Summarize: domain and adjacent market; users and roles; primary workflows; page types; information
density; interaction intensity; desired tone; explicit visual constraints and anti-goals; brand
trust points and front-of-house promises; screen archetypes that need golden references (especially
login/auth and the primary operational screen). If product-level signals are too vague, ask one
concise question. Do not infer brand tone from backend feature names.

## Phase 2: Retrieve candidates

```bash
python3 .agents/skills/vj-design-md-matcher/scripts/match_design_md.py --prd docs/product/requirements.md --limit 8
python3 .agents/skills/vj-design-md-matcher/scripts/match_design_md.py --query "<one-line brief>" --limit 8
```

The script uses the bundled cache at `assets/awesome-design-md/` first and merges missing entries from
`https://vibeui.top/site-assets/designs.js` when network is allowed. That vibeui catalog is the
authoritative source: it includes brand `design-md/*` entries plus generated style templates, so it
is larger than the GitHub `design-md` directory. Other flags: `--offline` (fail instead of network),
`--local <mirror>`, `--json`, `--download-cache [--cache <dir>]` to refresh the cache,
`--source github` (legacy fallback only).

## Phase 3: Recommend three

Read `references/matching-rubric.md`, then pick exactly three: a primary (closest product/workflow
fit), a secondary (complementary interaction or layout pattern), and a contrast (a useful constraint
or anti-pattern boundary). For each: why it fits, what to borrow, what to avoid, link to its
`DESIGN.md`. Override the script's ranking when its top picks are visually unsafe for the project, and say why.

## Phase 4: Confirm references

Show the three before writing anything and wait for confirmation, unless the user asked to proceed
without review. If one is rejected, replace only that one.

## Phase 4.5: Render direction candidates

Choose the direction from rendered pixels, not from text: two implementations can satisfy the same
prose and look completely different. Do not skip this phase.

1. Pick anchors: the highest-frequency operational screen (prefer table-list / console / review queue),
   plus the primary front-of-house screen when the product has one.
2. For each candidate direction and anchor, write one throwaway self-contained HTML (inline CSS,
   realistic mock data, ok / loading / failed / queued states) to
   `docs/reference/research/designs/candidates/`, plus an `index.html` side-by-side page.
   Follow `references/direction-candidate-craft.md`: each candidate is a committed visual thesis
   (mood + material + energy), not a skin-swap. Operational candidates stay calm and dense within the
   token system and are written inline. Front-of-house candidates may extend palette, type and depth
   within brand DNA, and are produced through `high-end-visual-design` / `design-taste-frontend`
   (or one focused design subagent) against a named reference bar (the site the user names, else
   Linear / Stripe / Resend), iterating to that bar; prose in this skill does not substitute for that pass.
3. Never render UI candidates with an image-generation model. Verified failures: garbled small text,
   direction collapsing toward a generic mean, AI-template look.
4. Run the litmus gate in `direction-candidate-craft.md` and drop failing candidates (lone centered card,
   no memorable anchor, slop). Show only passers, with desktop screenshots when browser tooling is
   available; otherwise ask the user to open `index.html`. The user picks one; at most one more
   re-render round.
5. Save the winner as golden: screenshots to `docs/reference/research/designs/golden/{archetype}.png`,
   or keep the winning `.html` when screenshots are unavailable.
6. Optional, brand-heavy front-of-house only: generate brand photography/texture (never UI) with an
   image tool, extract the palette from its pixels, and feed palette and assets into the chosen
   direction. Skip silently if the tool is unavailable; derive the palette from the references instead.

## Phase 5: Write `docs/project/DESIGN.md`

Sections: Product Design Direction; Reference Inspirations; Visual Principles; Color Tokens;
Typography Tokens; Layout Rules; Spacing Hierarchy; Component Rules; Interaction States;
Data-Dense UI Rules; Richness Floor by Screen-Type; Reference Skeletons (per screen archetype);
Golden Screens; Accessibility Rules; Do / Don't; Downstream Prompt Base.

- Fit the product, not the reference brands. Use tokens a frontend engineer can implement. Avoid
  one-note purple/blue gradients, decorative orbs, heavy beige themes and brand-copy colors unless the PRD demands them.
- Operational screens (tables, queues, editors) default to quiet, dense, scannable composition.
  Do not apply that austerity to front-of-house screens: they need a richness floor — intentional
  composition and product identity within the same tokens, never marketing gradient/orb/glass. A
  token system that yields a lone centered card on every screen has failed; state the floor explicitly
  so executors do not ship AC-minimal screens.
- **Spacing Hierarchy is layered, never a single range.** A flat rule like "operational screens use 8–16"
  gets executed as wall-to-wall 8px and reads as Excel, not Linear. Give hard ranges per level: page
  frame > region gaps > container padding > component rhythm > row height. Density lives in the data
  core; air lives at the page frame. Include machine-checkable floors (minimum page padding, minimum
  region gap, at most ~4 distinct gap values per screen) so screenshots can be measured.
- **Richness Floor by Screen-Type**: one-line minimum for each archetype in the PRD (front-of-house /
  dashboard / table-list / detail-reading / form-wizard). Richness means deliberate composition,
  identity and hierarchy, not decoration.
- **Reference Skeletons**: keep the matched references' structure and density after extracting tokens —
  distill each into a per-archetype skeleton (regions, order, density) re-skinned with these tokens,
  including the product's login/auth screen when the PRD has one, so executors copy a good skeleton
  instead of inventing a minimal one.
- Cover loading, empty, error, disabled, selected, dirty, saved, review-needed and destructive states when relevant.
- **Golden Screens**: list golden paths per archetype and state that implementation treats token text
  plus golden pixels as a dual source of truth; executors and visual auditors compare against the image,
  not only the prose.
- **Downstream Prompt Base**: reusable by `vj-plan` and `vj-work`; tells them to
  follow this `DESIGN.md` plus the approved golden references.

Outputs: the recommendation in chat; candidates under `designs/candidates/` and the golden under
`designs/golden/`; `docs/project/DESIGN.md` after confirmation or explicit proceed.
