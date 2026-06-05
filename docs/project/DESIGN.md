# DESIGN.md

> Project design source for the AI-driven internal business exam platform. Generated from `docs/project/requirements.md` and confirmed references from the vibeui / awesome-design-md library.

## Product Design Direction

This product is a high-density internal exam operations tool, not a marketing site. The UI must help two roles complete a full capability-verification loop without visual noise:

- `出题管理员`: input business material, define exam objectives, confirm AI knowledge points, review AI-generated questions, assemble papers, review subjective scoring, and confirm analysis.
- `员工考生`: take an assigned exam once, submit answers, and read confirmed scores, mistakes, weak points, and learning advice.

The design direction is "quiet operational clarity":

- calm light canvas with dense but readable tables, forms, and review queues
- status-first workflows for AI output, review, confirmation, failure, retry, and manual fallback
- content-friendly reading surfaces for business material, scoring rationale, wrong-answer explanations, and learning advice
- restrained accents used to clarify state, not decorate the page
- clear role boundaries and auditability in every exam-related surface

## Reference Inspirations

### Airtable

Source: https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/airtable/DESIGN.md

Use Airtable as the reference for structured object management: records, editable fields, filters, grouped lists, and calm white-canvas data surfaces.

Borrow:

- structured list and table density
- field labels, compact metadata, and editable record panels
- light canvas, dark ink, hairline borders, and restrained actions
- one clear primary action per screen region

Avoid:

- colorful brand card energy as a default pattern
- playful demo-card rhythm
- large marketing whitespace on operational screens

### Linear

Source: https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/linear.app/DESIGN.md

Use Linear as the reference for workflow precision: queues, state transitions, status tags, selected rows, and review loops.

Borrow:

- compact navigation and task-like state language
- exact status badges for pending, reviewing, confirmed, failed, and blocked states
- low-drama interaction styling
- strong hierarchy through spacing, alignment, and muted surfaces

Avoid:

- full dark theme as the default app chrome
- purple as the dominant accent
- overly developer-tool tone on learner-facing pages

### Mintlify

Source: https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/mintlify/DESIGN.md

Use Mintlify as the reference for knowledge and explanation surfaces: source material, scoring rationale, wrong-answer explanations, and learning advice.

Borrow:

- readable prose blocks with side context
- sidebar/prose/detail patterns for knowledge-heavy views
- code-like monospace treatment only for structured IDs, schemas, and AI output traces
- green and neutral feedback for confirmed guidance

Avoid:

- documentation-site spaciousness on admin pages
- atmospheric hero gradients
- marketing-style product mockup framing

## Visual Principles

1. Operational first.
   Every screen should make the next action, current status, and blocking condition obvious within one scan.

2. Data is the interface.
   Tables, forms, question lists, scoring rows, and result records are primary UI, not secondary content inside decorative cards.

3. AI output is provisional until confirmed.
   AI-generated knowledge points, questions, subjective scores, and learning advice must be visually distinct from confirmed records.

4. State beats decoration.
   Use color, badges, icons, and row treatment to show workflow state. Do not add decorative gradients, background blobs, or large illustrations.

5. Compact, not cramped.
   Use dense spacing for repeated rows and controls, but keep prose, question stems, and scoring rationales readable.

6. Role boundaries stay visible.
   Admin and employee surfaces should share one system, but employee result views should be calmer and more explanatory than admin review queues.

## Color Tokens

Use light mode as the default. Dark surfaces are reserved for small emphasis panels or code/AI trace blocks, not full app chrome.

```yaml
colors:
  canvas: "#F8FAFC"
  surface: "#FFFFFF"
  surface-muted: "#F1F5F9"
  surface-raised: "#FFFFFF"
  surface-selected: "#EAF4F2"
  surface-ai: "#F6F3FF"
  surface-warning: "#FFF7E6"
  surface-danger: "#FFF1F0"

  ink: "#111827"
  ink-muted: "#475569"
  ink-subtle: "#64748B"
  ink-disabled: "#94A3B8"
  inverse-ink: "#FFFFFF"

  border: "#D8DEE8"
  border-strong: "#B8C2D0"
  border-focus: "#1D4ED8"

  primary: "#0F3D3E"
  primary-hover: "#0B3031"
  primary-pressed: "#082829"
  on-primary: "#FFFFFF"

  link: "#1D4ED8"
  info: "#2563EB"
  ai: "#6D5BD0"
  success: "#0F7A4F"
  warning: "#B7791F"
  danger: "#B42318"
  neutral: "#64748B"

  score-high: "#0F7A4F"
  score-mid: "#B7791F"
  score-low: "#B42318"
```

Color rules:

- Primary action uses `primary`, not blue. Blue is for links, focus, and informational affordances.
- `ai` is a secondary accent for provisional AI output only. It must not dominate the page.
- Use `success`, `warning`, and `danger` only for status and validation.
- Avoid large saturated color surfaces. When a state needs a tinted background, use the corresponding `surface-*` token.
- Never use gradient or blob backgrounds for app screens.

## Typography Tokens

Use system UI fonts. Do not require proprietary reference fonts.

```yaml
typography:
  font-sans: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
  font-mono: "Geist Mono, SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace"

  page-title:
    fontSize: 24px
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: 0
  section-title:
    fontSize: 18px
    fontWeight: 650
    lineHeight: 1.35
    letterSpacing: 0
  panel-title:
    fontSize: 16px
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: 0
  body:
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: 0
  body-strong:
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: 0
  caption:
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0
  table:
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.35
    letterSpacing: 0
  mono:
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.45
    letterSpacing: 0
```

Typography rules:

- Reserve `page-title` for page headers only.
- Use `section-title` inside dense admin pages; do not use hero-scale type in panels.
- Question stems and scoring rationale use `body` with comfortable line-height.
- IDs, schemas, trace snippets, and raw AI parse errors may use `font-mono`.
- Do not scale type with viewport width.

## Layout Rules

### App Shell

- Use a persistent left sidebar for admin workflows.
- Use a simpler top bar or narrow shell for employee exam-taking, where focus should remain on the question flow.
- Keep global navigation compact and predictable.
- Show current role, active workspace/session, and user identity in the shell.

Recommended desktop shell:

```yaml
shell:
  sidebarWidth: 248px
  topbarHeight: 56px
  contentMaxWidth: none
  contentPaddingDesktop: 24px
  contentPaddingTablet: 20px
  contentPaddingMobile: 16px
```

### Page Structure

Use unframed page sections with constrained inner content. Do not put UI cards inside other cards.

Admin pages:

- Page header: title, short status/meta line, primary action cluster.
- Optional filter/action bar.
- Main content: table/list/review queue with details drawer or split pane.
- Right or bottom detail region when reviewing AI output.

Employee pages:

- Clear exam identity and progress.
- One question group or one question at a time on narrow screens.
- Persistent submit/progress affordance without blocking reading.
- Result pages prioritize score, mistakes, weak points, and advice in that order.

### Spacing

```yaml
spacing:
  1: 4px
  2: 8px
  3: 12px
  4: 16px
  5: 20px
  6: 24px
  8: 32px
  10: 40px
  12: 48px
```

Spacing rules:

- Dense rows: 8px vertical padding.
- Standard form fields: 12px vertical rhythm.
- Panel padding: 16px for dense panels, 20px for detail panels, 24px for major page regions.
- Major vertical separation inside app pages should rarely exceed 32px.
- Avoid landing-page spacing such as 96px section gaps inside the app.

### Radius And Elevation

```yaml
radius:
  xs: 3px
  sm: 4px
  md: 6px
  lg: 8px
  full: 9999px
```

Rules:

- Cards, panels, tables, dialogs, and drawers use 8px or less.
- Badges use `full` or 4px depending on density.
- Inputs and select controls use 6px.
- Elevation is mostly border-based. Use shadows only for popovers, menus, dialogs, and drawers.

## Component Rules

### Buttons

Use icon buttons for tool actions where a common symbol exists. Use text buttons for commands that need clarity.

```yaml
button-primary:
  background: "{colors.primary}"
  color: "{colors.on-primary}"
  height: 36px
  padding: "0 14px"
  radius: "{radius.md}"
  typography: "{typography.body-strong}"

button-secondary:
  background: "{colors.surface}"
  color: "{colors.ink}"
  border: "1px solid {colors.border}"
  height: 36px
  padding: "0 14px"
  radius: "{radius.md}"

button-ghost:
  background: "transparent"
  color: "{colors.ink-muted}"
  height: 32px
  padding: "0 10px"
  radius: "{radius.sm}"

button-danger:
  background: "{colors.danger}"
  color: "{colors.inverse-ink}"
  height: 36px
  padding: "0 14px"
  radius: "{radius.md}"
```

Button rules:

- One primary action per page region.
- Destructive actions must require explicit confirmation when they affect persisted exam data.
- Loading buttons keep their width stable.
- Disabled buttons must show why the action is unavailable near the control or in the surrounding state text.

### Forms

Forms are central to material input, exam objective creation, question editing, and manual scoring.

Rules:

- Labels are always visible above fields.
- Required fields show a compact required badge or marker.
- Validation appears inline under the field and in a page-level summary when multiple fields fail.
- Multi-line fields for material, question stems, answers, and scoring rationale use readable 14px body text and line-height 1.55.
- Long forms use section headers and sticky action bars.
- Save, confirm, and cancel actions must remain visible near the bottom or in a sticky footer.

### Tables And Lists

Tables represent materials, objectives, questions, papers, submissions, scoring tasks, and records.

Rules:

- Header row: muted surface, 13px semibold, sticky when useful.
- Row height: 40px compact, 48px standard, 56px when a row has secondary metadata.
- First column should identify the object clearly.
- Status, owner, updated time, score, and action columns must be scannable.
- Use row selection for batch actions only when the workflow needs it.
- Empty tables show the next useful action, not a blank illustration.

### Status Badges

Status badges must use consistent labels across the product.

```yaml
statuses:
  draft:
    label: "草稿"
    tone: neutral
  ai-generated:
    label: "AI 已生成"
    tone: ai
  needs-review:
    label: "待审核"
    tone: warning
  needs-confirm:
    label: "待确认"
    tone: warning
  confirmed:
    label: "已确认"
    tone: success
  assigned:
    label: "已分配"
    tone: info
  submitted:
    label: "已提交"
    tone: info
  grading:
    label: "评分中"
    tone: ai
  needs-manual-score:
    label: "待人工评分"
    tone: warning
  failed:
    label: "失败"
    tone: danger
  completed:
    label: "已完成"
    tone: success
```

Badge rules:

- Badges use tinted backgrounds, not saturated fills.
- Pair badges with icons only when the icon adds recognition: check, clock, alert, refresh, lock.
- A failed AI state must always include retry or manual fallback nearby.

### Review Queues

Review queues appear for knowledge points, AI questions, subjective scoring, and learning advice.

Rules:

- Split view is preferred on desktop: queue/list left, selected item detail right.
- Show source material context, AI output, editable final value, and confirmation action in one scan.
- Preserve AI original value when the admin edits final score or content.
- Use diff-like treatment only when comparing AI output to edited content.
- Confirmation actions should be explicit: "确认知识点", "确认题目", "采纳 AI 分", "保存人工分", "确认分析".

### Exam Taking

Employee exam-taking should be calmer than admin pages.

Rules:

- Show paper title, total questions, progress, and submit state.
- Question cards are unnested panels with clear number, type, score, stem, and answer controls.
- Radio and checkbox choices need generous touch targets.
- Subjective answers use a stable textarea with autosave or clear unsaved indication if implemented.
- Unanswered questions are highlighted in the progress summary before submit.
- The final submit action must explain that the same paper cannot be submitted again.

### Result And Advice Views

Result pages combine scoring and learning content.

Rules:

- Start with total score and completion state.
- Then show wrong questions with correct answer or scoring rationale.
- Then show weak knowledge points grouped by related questions.
- Then show learning advice with source-linked context when possible.
- Do not expose unconfirmed AI analysis to employees.

## Interaction States

Every interactive component must define these states when relevant:

- default
- hover
- focus-visible
- active/pressed
- disabled
- loading
- selected
- dirty/unsaved
- saved
- error
- empty

AI workflow states:

- idle: no AI result yet
- running: show progress text and disable duplicate trigger
- generated: result exists but is provisional
- parse-error: schema validation failed
- failed: call failed or timed out
- retrying: user has triggered another attempt
- manual-fallback: admin is entering replacement content
- confirmed: human-confirmed result saved

State rules:

- Long AI actions must not look frozen. Show stage text such as "正在提取知识点" or "正在生成评分依据".
- Failed states must explain what failed and offer a retry or manual path.
- Saved/confirmed states should be visibly calmer than pending states.
- Use optimistic UI only when rollback is easy and clear.

## Data-Dense UI Rules

The product has many structured records, so density must be deliberate.

- Prefer tables for object inventories and queues.
- Prefer split panes for review.
- Prefer drawers for quick object details that do not require full-page focus.
- Prefer dedicated pages for long editing workflows.
- Keep filters in a compact toolbar with persistent chips for active filters.
- Show metadata in predictable positions: owner/role, status, updated time, source, AI state.
- Use badges and compact secondary text before adding new columns.
- Truncate long material names and question stems in tables, but reveal full text in detail panes.
- Keep row actions icon-first where common: view, edit, confirm, retry, delete.
- Avoid repeated large cards for lists of questions or records.

## Accessibility Rules

- All text must meet WCAG AA contrast.
- Focus rings use `border-focus` and must be visible on keyboard navigation.
- Touch targets should be at least 40px in dense admin UI and 44px on employee exam pages.
- Status must not rely on color alone; pair color with label and, where useful, icon.
- Error text must identify the field or operation that failed.
- Tables must expose meaningful headers and row labels.
- Forms must support keyboard-only completion.
- Dialogs must trap focus and return focus to the triggering control.
- Motion should be subtle and optional; never use motion to hide latency.

## Do / Don't

Do:

- Use light, quiet operational surfaces.
- Use compact tables, filters, and review split panes.
- Keep AI output visually provisional until confirmed.
- Show manual fallback paths next to failed AI states.
- Use green/teal for confirmed progress, amber for review, red for blocking failure, and purple only for AI provisional content.
- Keep employee result pages readable and supportive.

Don't:

- Do not turn the app into a dark developer console.
- Do not use marketing hero layouts for the product shell.
- Do not add gradient blobs, bokeh, or decorative background shapes.
- Do not use brand-like Airtable colors as large default surfaces.
- Do not bury destructive or irreversible actions in ambiguous icon-only controls.
- Do not show unconfirmed AI analysis to employees.
- Do not make every object a card when a table or list would scan better.

## Downstream Prompt Base

Use this base when generating UI prompts, mockups, or frontend implementation details:

```text
Follow docs/project/DESIGN.md as the stable design source for this project. Design a high-density internal AI exam operations tool with calm light surfaces, compact tables, structured forms, review queues, and clear AI workflow states. Use a restrained palette: dark teal primary actions, neutral white/slate surfaces, blue for links/info, green for confirmed success, amber for review-needed states, red for failures, and purple only for provisional AI output. Avoid marketing heroes, decorative gradients, background blobs, glassmorphism, heavy dark mode, and brand-copy styling from Airtable, Linear, or Mintlify. Admin pages should prioritize scanning, filtering, status badges, split-pane review, and explicit confirm/retry/manual-fallback actions. Employee exam and result pages should be quieter, readable, and focused on progress, answers, score, wrong questions, weak points, and confirmed advice.
```

## Screen-Level Guidance

### Login

- Simple centered panel on light canvas.
- User identity selection/input must show role, name, email, and user ID.
- Invalid account state uses inline error and a clear retry path.

### Material And Objective Setup

- Use a two-column layout on desktop: material input/source on the left, exam objective form on the right.
- Show the six objective fields as required sections.
- File upload and text paste should be visually equivalent paths.
- Knowledge extraction trigger is disabled until material and required objective fields are present.

### Knowledge Point Confirmation

- Use a review split pane.
- Left: extracted knowledge point list with status and source snippets.
- Right: selected knowledge point editor with source context, AI confidence if available, and confirm/delete actions.
- Empty and AI failed states must offer manual addition.

### Question Generation And Review

- Use a queue grouped by type and status.
- Each question row shows type, score, linked knowledge points, validation status, and review state.
- Detail pane shows stem, choices, answer, scoring points, linked knowledge, and edit controls.
- Validation failures are shown as blocking issue chips.

### Paper Assembly

- Use a selected-question table plus paper summary panel.
- Show total score, question count, type coverage, subjective count, and assignment target.
- Prevent assembly when minimum rule checks fail; list exact missing conditions.

### Exam Taking

- Employee-focused shell with clear progress and stable submit bar.
- Question content must be easy to read.
- Show unanswered question summary before final submit.
- Explain single-submit constraint near the submit action.

### Grading Review

- Use a scoring queue for subjective answers.
- Detail pane shows employee answer, reference answer/scoring points, AI score, AI rationale, final score input, and confirm/manual override actions.
- Preserve the AI original score and rationale when manually changed.

### Results And Analysis

- Admin view: table of submissions and review/analysis status.
- Employee view: total score, wrong questions, weak points, and confirmed advice.
- Weak points should be grouped by knowledge point and linked back to wrong questions.
- Unconfirmed analysis is hidden from employees and visible to admin as pending.
