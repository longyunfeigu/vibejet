# Feature-Tree Coverage Sync (Phase 5)

After Phase 4 passes, record that the new cases cover their product feature, so the coverage
metric stays in step with prd-to-bdd.

## Background (read once)

- The feature tree's backbone is `Product/feature-catalog.md` — the PM-maintained index of
  `Product/requirements/` (the single source for dev + tests + features). `docs/feature-tree/feature-tree.src.md`
  is **GENERATED** from the catalog by `core/runner/build-feature-tree-src.mjs` (run automatically as the
  first step of `npm run coverage:tree`). **Never hand-edit feature-tree.src.md.**
- Only **built** features (`Completed` / `In-Dev` in the catalog) are leaves (the coverage denominator).
  `Draft` / `Backlog` / `Roadmap` features are listed in `planned-features.md` and excluded.
- Each leaf carries `@cases:` with Case-ID **prefixes** (e.g. `VA-SHL*`) meaning "this feature has coverage".
  A leaf is covered if any automated case matches one of its prefixes. `@cases` values are carried across
  regeneration by feature name, so an `@cases` edit on a leaf persists even though the file is regenerated.

## Steps

### 1. Identify the product feature
The PRD/delivery doc names a product capability. It should already exist as a row in
`Product/feature-catalog.md` (PM adds it there when the PRD lands). Find the matching leaf in
`docs/feature-tree/feature-tree.src.md` (a `-` line under the right `# 功能区 > ## 功能场景`).

### 2. Attach the new Case-ID prefix
Add the new cases' `{FEATURE_CODE}*` to that leaf's `@cases:` (comma-separated if it already has some):
```
- Share links with access codes / 带访问码的分享链接 @cases: VA-SHL*
```
Because `coverage:tree` regenerates the file but preserves `@cases` by feature name, this survives.

### 3. If the feature has no leaf
That means the catalog has no **built** row for it. Do NOT add a leaf to `feature-tree.src.md` (it is generated).
Instead:
- If the feature is genuinely built, it belongs in `Product/feature-catalog.md` with status `Completed`/`In-Dev`
  — flag in your Output Report: "feature-catalog.md missing built row for '{feature}' (PM to add)".
- If it is still `Draft`/`Backlog`, it correctly lives in `planned-features.md` (not yet a coverage target);
  the new cases will show as **untracked** until the feature is marked built — that is expected.

### 4. Recompute and verify
```bash
npm run coverage:tree -- --write
```
Confirm the new `{FEATURE_CODE}` cases are not under "Untracked automated cases" in `coverage-report.md`
(unless intentionally testing a not-yet-built feature, per step 3).

### 5. Add a Chinese feature name if new
If you flagged a new built feature for the catalog, also add its `EN<TAB>CN` line to
`docs/feature-tree/feature-names-cn.tsv` so the Chinese tree renders a Chinese name.

### 6. Commit
Commit `feature-tree.src.md` + regenerated `FEATURE-TREE*.md` / `coverage-report.md` (+ `feature-names-cn.tsv` if changed):
```
feat(feature-tree): cover "{product feature}" via {FEATURE_CODE}* ({n} new cases)
```

## Notes
- Pending cases (`.pending.feature`) are NOT automated → do not make a leaf covered until activated.
- Delete/rename/unautomate a test → re-run `coverage:tree`; the leaf flips back to a gap automatically.
- Do NOT hand-edit the generated files (`feature-tree.src.md`, `FEATURE-TREE*.md`, `coverage-report.md`, `planned-features.md`).
