---
name: ui-design-review
description: >
  Read-only design critic for a React internal dashboard. Grades a component or
  view against the internal-ui-taste rules and tokens.css, and reports prioritized
  findings with file:line — it does NOT edit. Use before merging a UI change, when
  asked "does this look right / is this consistent?", or to spot-check a view. The
  reviewer half of the author/auditor split. Zero dependencies.
---

# ui-design-review

The companion auditor to `internal-ui-taste`: that skill *builds* taste, this one
*grades* it — and never edits. Same separation as `playbook-author` vs
`investigation-audit` elsewhere in this kit. Works from the code (and a screenshot
if one is provided); no browser tooling required.

## How to review

**Step 0 — run the deterministic scanner first.** Don't eyeball mechanical bugs you
can't catch reliably; let code find them:
```bash
python -m engine.ui_scan <path-to-component-or-dir>
```
It reports exact `file:line` findings for 30 React/FastAPI rules (clickable
non-buttons, `length && 0` leaks, index-as-key, missing modal a11y, CORS
wildcard+credentials, missing dark variants, plus cockpit-specific
`status-color-only` and `list-no-pagination`) with a fix for each. Fold these into
your report as confirmed findings, then spend your judgement on the taste/context
checks below that a scanner can't see.

**Then** read the target component(s), `tokens.css`, and nearby styles. Score each
check `PASS / FAIL / N-A` with `file:line` and the specific problem. Rank findings by
severity. Hand the report back — do not rewrite the component yourself; route fixes
to `internal-ui-taste`.

## Checklist (graded against internal-ui-taste + tokens.css)

**1. Token adherence**
- Spacing uses the 4px scale tokens — flag any magic `7px`/`13px`/`22px`.
- Colors come from tokens (`--color-*`) — flag hardcoded hexes, especially greys and status colors.
- Type sizes/weights/families come from the scale — flag one-off font sizes.

**2. Status palette consistency**
- Severity/state colors are used semantically and identically across table, chips, and timeline (`critical/warning/info/healthy`, `confirmed/refuted/needs-data/open`). Flag a green used decoratively, or two different reds for "critical".
- Status is never color-only (must pair with text/icon) — overlaps a11y but matters for taste too.

**3. Hierarchy & alignment**
- Clear visual hierarchy: one primary action per region, titles distinct from body. Flag flat, undifferentiated walls of text.
- Shared alignment edges for labels/values/controls. Flag ragged left edges and mis-aligned form rows — the most visible amateur tell.
- Left-aligned, scannable layout. Flag centered content columns and centered data.

**4. Density (cockpit, not landing page)**
- Compact but scale-aligned (rows ~28–32px, padding on the scale). Flag both bloated whitespace and cramped off-scale padding.
- No marketing patterns: hero blocks, oversized headings, decorative imagery. Flag them.

**5. State coverage**
- Loading / empty / error / needs-data all present and styled. Flag any async surface missing one (the #1 "demo not tool" gap).

**6. Motion restraint**
- Only motivated, ~120–200ms state-feedback transitions; `prefers-reduced-motion` honored. Flag decorative/scroll animation, parallax, marquees.

**7. Anti-slop tells**
- Flag: purple/indigo gradients & glassmorphism, emoji-as-functional-icons, 4+ competing accent colors, heavy zebra + heavy borders + shadows stacked, skeletons with no resolve path, truncation with no way to see the full value.

## Output

A concise report:
- **Verdict:** SHARP / NEEDS-WORK / SLOP.
- **Findings:** ranked, each `file:line` → problem → which internal-ui-taste rule it breaks.
- **Top fix:** the single highest-impact change to make first.

## Hard rule

**Read-only.** If you want to edit, stop and report instead, then invoke
`internal-ui-taste` to apply the fixes. Critic and author stay separate.
