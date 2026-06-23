---
name: ui-accessibility-audit
description: >
  Audit and fix accessibility in a React internal tool by reading the code — no
  axe-core, no browser tooling, no installs. Use when asked to check a11y, make
  the UI keyboard-operable, fix WCAG/ARIA issues, or before shipping a dashboard
  view. Targets WCAG 2.2 AA for a daily, keyboard-heavy on-call tool. Mined and
  re-implemented dependency-free from wcag-audit-patterns / AccessLint.
---

# ui-accessibility-audit

An on-call engineer drives an incident dashboard from the keyboard at 3am, often
on a bad connection, sometimes with a screen reader. Accessibility here isn't
compliance theatre — it's whether the tool is *usable under stress*. This skill
audits by **reading the JSX/CSS** and proposes fixes; it needs no axe-core or
Playwright, so it runs in a locked-down env.

## How to run the audit

**Step 0 — run the static scanner for the mechanical a11y rules:**
```bash
python -m engine.ui_scan <path-to-component-or-dir>
```
It catches the regex-detectable failures exactly (`clickable-nonbutton`,
`icon-button-no-label`, `img-no-alt`, `input-no-label`, `modal-no-a11y`,
`dialog-no-label`, `nested-interactive`, `positive-tabindex`, `modal-no-escape`, …)
with `file:line` and a fix. Take those as confirmed, then do the manual checks below
— focus order, live regions, contrast-in-context, keyboard interaction of custom
widgets — which a static scan can't verify.

Read the target component(s) and check each item below. Report findings as
`PASS / FAIL / N-A` with `file:line` and a concrete fix. Then apply the fixes
incrementally (highest-severity first). Re-read to confirm.

## Checklist (WCAG 2.2 AA, ranked by impact for this tool)

**1. Keyboard operability (highest priority)**
- Every interactive element is reachable and operable by keyboard (Tab/Enter/Space/arrows). No click-only `<div onClick>` — use `<button>`, or add `role` + `tabIndex={0}` + key handlers.
- Logical focus order matches visual order. Modals/drawers trap focus and restore it on close.
- Visible focus on everything focusable (the `--focus-ring` token from tokens.css). Never `outline: none` without a replacement.
- Custom widgets (sortable table headers, the timeline, command palette) have working keyboard interaction, not just mouse.

**2. Semantic structure**
- Real semantic elements: `<button>`, `<nav>`, `<main>`, `<table>`, `<th scope="col">`, `<ul>` — not `<div>` soup. Screen readers and keyboard behaviour come free with the right element.
- One `<h1>` per view; headings descend without skipping levels.
- Data tables use `<thead>/<th scope>`; don't fake a table with flex divs when it's tabular data (query results, metrics).

**3. Names & labels**
- Every input/select has an associated `<label>` (or `aria-label`). Icon-only buttons (copy, expand, dismiss) have `aria-label`.
- Links/buttons have descriptive text — no bare "click here" / lone icons without names.

**4. Status not by color alone (critical for an ops tool)**
- Severity/state (sev1, confirmed, refuted, needs-data) must carry a text label or icon, not just red/green — colorblind users can't read color-only status. Pair the status chip color with its word.
- Contrast ≥ 4.5:1 for text, ≥ 3:1 for UI borders/icons. The tokens.css palette is tuned for this; flag any hardcoded low-contrast greys.

**5. Async & live regions (your streaming agent + queries)**
- Streaming agent replies and "query running… / done" updates go in an `aria-live="polite"` region so they're announced, not silently swapped.
- Loading/empty/error states are perceivable to screen readers, not just spinners.
- Errors are programmatically associated with their field/context, not color-only.

**6. Motion & preference**
- All animation respects `prefers-reduced-motion` (the tokens.css guard covers the basics; check JS-driven motion too).

**7. Forms & destructive actions**
- Destructive actions (anything mutating) need a clear, focusable confirm — consistent with the kit's "human approves before action" rule.

## Output

A short report: overall verdict, the FAIL items with `file:line` + fix, and the
single highest-impact fix to do first. Then apply fixes — don't add an a11y
library; fix the markup. Keyboard operability and labels first; they unblock the
most users.
