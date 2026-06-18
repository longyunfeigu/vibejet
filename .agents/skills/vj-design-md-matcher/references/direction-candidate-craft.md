# Direction Candidate Craft

Use this in Phase 4.5 when producing direction candidates. The matcher's procedure (pick anchors →
render throwaway HTML per direction → side-by-side `index.html` → pixel decision → persist golden)
stays as-is. This file raises the *craft* of each candidate so the rendered options are bold and
distinctive, not timid skin-swaps. It is a positive recipe: a candidate either matches the shape
below or it is a reject.

Adapted from front-end design craft practice. Three adaptations are deliberate and must hold —
they are where generic craft guidance is wrong for this matcher:

- **Front-of-house candidates may exceed the operational token system** (within brand DNA). Their
  whole job is to set a higher ceiling than the calm operational baseline. Do **not** defer to the
  existing system for front-of-house the way generic "match what exists" guidance would.
- **Keep the project's real fonts.** Use type with intent, but front-of-house candidates must stay
  CJK-safe — do not drop a configured body font (e.g. Inter + CJK fallback) just to look "designed".
- **Two anchors, two tracks.** Operational and front-of-house candidates are judged by different
  bars (§3). One mood does not fit both.

## 1. Commit to a thesis per candidate

Each candidate starts from one written **visual thesis** — one sentence: *mood + material + energy*.
Render the candidate to express that thesis, not to nudge the previous one.

- Good: "Editorial authority — oversized display headline carries the page, hairline rules, generous
  whitespace, one decisive accent."
- Bad: "Variant B — same layout, different colors."

If two candidates share a thesis, you have one candidate. Make them genuinely different bets.

## 2. 调调 catalog (a menu to commit to, not a checklist)

Pick distinct bets across this range; invent one if it fits the product better:

`editorial` · `luxe-minimal` · `dark-technical` · `narrative-depth` · `brutalist` · `industrial` ·
`retro-futuristic` · `organic` · `maximalist` · `art-deco`

For each, ask: *what is the one thing someone remembers?* A candidate with no memorable anchor is a reject.

## 3. Two-track bar

| Track | Anchor screens | Bar |
| --- | --- | --- |
| **Operational** | dashboard, table, queue, editor, review console | Calm dense console: strong type + spacing hierarchy, few colors, minimal chrome, density in the data core. Bold ≠ decorated. Do **not** exceed the operational token system. |
| **Front-of-house** | login, signup, landing, onboarding, empty first-run | Poster, not document. One strong visual anchor, a committed aesthetic, product identity unmistakable. **May extend** palette / type / depth beyond the operational tokens, within brand DNA (keep the brand accent's role; it is still the same product). |

## 4. Craft defaults (front-of-house candidates)

- **Composition first.** Treat the first viewport as a poster: whitespace, scale, alignment, contrast
  before chrome. Default cardless; a card only where it *is* the interaction (the login/account card qualifies).
- **Typography.** A real hierarchy with decisive scale jumps. Type with intent; stay CJK-safe.
- **Color.** A dominant field + one decisive accent beats a timid even palette. Keep the brand accent's
  role; front-of-house may add controlled depth (tonal range, one supporting hue).
- **Motion.** Name 1–2 intentional motions (entrance, hover/reveal); implement only if the candidate
  still reads well as a still screenshot.
- **Copy stays product language.** No design commentary, no prompt language, no marketing fluff bleeding
  into a trust tool.

## 5. Anti-slop hard rules (reject before the user ever sees it)

- Lone centered form card as the whole front-of-house screen.
- Generic SaaS card grid as the first impression.
- Decorative gradient / orb / glass / abstract background standing in for a real anchor or real content.
- Purple-on-white default, or a dark theme used as decoration rather than as the committed thesis.
- Multiple competing accent colors.
- Unreadable text over a busy area; missing focus states.

## 6. Litmus gate — run BEFORE showing candidates to the user

Drop any candidate that fails:

- Is the product unmistakable in the first screen?
- Is there one strong visual anchor (not just chrome)?
- Would it still feel premium with all decorative shadows removed?
- Does it express its thesis — and is that thesis different from the others?
- (Front-of-house) Does it clear the richness floor — ≥2 intentional regions, identity + action, no lone centered card?

## 7. Front-of-house: required craft engine + reference target

Prose in this file does **not** substitute for design craft. This is empirical, not a preference:
front-of-house candidates hand-authored by an agent following §1–§6 inline come out *competent but
not high-end*; the same brief run through a dedicated craft pass comes out genuinely high-end. So §1–§6
are the *bar to check against*, not a recipe to execute by hand. For front-of-house, two things are
**required** (operational candidates ignore this section — stay inline, no taste skill, dense-admin craft only):

1. **Generate via the dedicated craft engine — not inline.** Produce front-of-house candidates by
   invoking `high-end-visual-design` (or `design-taste-frontend`), or by dispatching one focused design
   subagent that invokes it in a fresh context devoted only to the design. Do not hand-author them from
   §1–§6.
2. **Anchor to a concrete reference — never to the word "高级".** "高级" is unactionable as a word; every
   guess misses. Before generating, obtain a reference target: a real login/site the user names as 高级
   (URL or screenshot). If the user gives none, ask once; if still none, proceed against an explicitly
   **named** default bar (e.g. Linear / Stripe / Resend login) and state which. Generate to *match that
   bar's caliber*, re-skinned to brand DNA — not to invent "高级" from scratch.
3. **Iterate to the bar.** Render → self-critique against the reference + the §6 litmus → redo until it
   clears (or hand to `ce-design-iterator`). Never present a first draft as the candidate.
