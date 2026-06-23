---
name: internal-ui-taste
description: >
  Make an internal React data/ops dashboard look sharp, dense, and trustworthy —
  without adding dependencies. Use when asked to improve, fix, restyle, or "make
  the UI less ugly" on an internal tool: incident dashboards, admin panels, query
  consoles, agent chat UIs. Tuned for a DATA COCKPIT, not a landing page. Plain
  React + CSS only by default (no Tailwind/Framer/GSAP required). Mined and
  re-tuned from github.com/Leonxlnx/taste-skill for locked-down environments.
---

# internal-ui-taste

You are improving an **internal incident-investigation dashboard** (React frontend,
FastAPI backend). The goal is a tool that an on-call engineer trusts at 3am: dense,
scannable, calm, and honest about state. This is **not** a marketing site — there
is no hero, no scroll choreography, no bento grid. Density and clarity beat flair.

## 0. Hard constraints (do not violate)

- **No new dependencies by default.** Plain React + CSS (CSS Modules, a stylesheet,
  or inline styles using design tokens). Do **not** add Tailwind, Framer Motion,
  GSAP, shadcn, or icon packages unless the user explicitly confirms installs are
  allowed. If you think a library would help, *suggest it* — don't add it.
- **CSS-only motion**, and always honor `prefers-reduced-motion`.
- **Accessibility AA**: real focus states, 4.5:1 text contrast, semantic HTML,
  keyboard-navigable. An internal tool used daily must be operable without a mouse.
- **Edit incrementally.** Fix the worst hierarchy/spacing/state problem first;
  don't rewrite a working component to restyle it.

## 1. Dials (preset for an ops tool — invert the usual "pretty" defaults)

```
DESIGN_VARIANCE: 3   (calm, consistent, predictable layouts — not asymmetric/playful)
MOTION_INTENSITY: 2  (state-transition feedback only; nothing decorative)
VISUAL_DENSITY:   7   (data cockpit — pack information, but with a real spacing scale)
```

## 2. Foundations — define tokens once, reuse everywhere

Put these in one place (`tokens.css` or a `theme.ts`) and reference them. The #1
cause of "ugly internal tool" is ad-hoc spacing/colors per component.

- **Spacing scale (4px base):** 4, 8, 12, 16, 24, 32. No magic `13px`, `7px`,
  `22px`. Every margin/padding/gap snaps to the scale.
- **Type scale:** ~12 / 13 / 14 (body) / 16 / 20 / 24. One sans family for UI
  (system stack is fine: `-apple-system, Segoe UI, Roboto, sans-serif`). **One
  monospace family** for IDs, timestamps, query output, log lines, metric values.
- **One accent color, locked** across the whole app (links, primary buttons, active
  nav). Pick a calm blue/indigo — avoid the purple-gradient "AI slop" look.
- **Semantic status palette (define exactly these, reuse everywhere):**
  - critical/sev1 = red · warning/sev2 = amber · info/sev3 = blue · healthy = green
  - Investigation states (match the engine): `confirmed` = green, `refuted` = muted
    grey, `needs-data` = amber, `open` = neutral. Use the *same* colors in tables,
    chips, and the timeline so a glance reads consistently.
- **Neutrals:** a 5–6 step grey ramp for bg / surface / border / muted-text / text.
  Borders should be subtle (`1px` low-contrast), not black.

## 3. Layout — a scannable cockpit

- **No centered content columns.** Left-align everything; the eye scans down a left
  edge. Full-width tables and panels.
- **A stable three-region shell works well here:** left nav / context (incidents,
  services) · main results area (timeline, query output, RCA draft) · the agent
  **chat panel** (right or bottom dock). Keep it stable — don't relayout per view.
- **Alignment grid:** labels, values, and controls share alignment edges. Mismatched
  left edges are the most visible "amateur" tell.
- **Group with whitespace and subtle dividers, not boxes-in-boxes.** Avoid nested
  cards with competing borders/shadows. One elevation level for surfaces.
- **Sticky headers** for long tables and the timeline so context survives scroll.

## 4. Domain components (where the real wins are)

This is an incident tool. Style the things it actually shows:

- **Timeline** (deploys, alerts, metric inflections): vertical, monospace
  timestamps in a fixed-width left gutter, a colored dot per event keyed to the
  status palette, the suspect/trigger event visually emphasized (heavier weight or
  a left accent border — not a different font).
- **Evidence / source citations:** render each cited source (a query name, TSG
  section, log line) as a small monospace **chip** next to the claim. Trust comes
  from showing the receipts — make citations visible, not hidden in tooltips.
- **DRAFT RCA rendering:** a clear **"DRAFT — needs sign-off"** banner at top (amber,
  not alarming red). Render `<NEEDS-DATA>` gaps and unverified claims as their own
  amber-tagged list, visually distinct from confirmed findings. Confidence shown as
  a labeled value (`confidence 85%`), optionally a thin bar — never a vague vibe.
- **Data tables (query results):** right-align numbers, monospace numeric/ID
  columns, sticky header, subtle row separation (hover highlight > heavy zebra),
  truncate long cells with an accessible tooltip for the full value. Density 7:
  compact row height (~28–32px), but padding still snaps to the spacing scale.
- **Log / raw query output:** monospace block, controlled wrapping, a copy button,
  muted line numbers if helpful. Don't let it blow out the layout width.
- **Agent chat panel:** clearly distinguish user vs agent turns (alignment +
  surface tint, not loud bubbles). Show tool/query calls as collapsible monospace
  blocks. Support streaming with a calm typing indicator. Keep input pinned bottom.

## 5. State coverage (the difference between "demo" and "tool")

Every async surface needs all four — most ugly internal tools skip three of them:

- **Loading:** a real skeleton or inline spinner with context ("running query…"),
  not a blank flash.
- **Empty:** a short, specific message + the next action ("No incidents in this
  window. Widen the range."). Never a blank panel.
- **Error:** show what failed and a retry; surface FastAPI error detail, don't
  swallow it.
- **Needs-data / partial:** when the investigation is blocked on a missing signal,
  say so explicitly (ties to the kit's `<NEEDS-DATA>`), don't render a fake-complete
  result.

## 6. Motion (minimal, motivated, CSS-only)

- Allowed: ~120–200ms ease transitions for state changes (row expand, panel open,
  chip appear), subtle hover feedback, a calm streaming indicator.
- Banned: decorative scroll animation, parallax, marquees, bouncing, anything that
  delays an engineer reading data. Wrap all of it in
  `@media (prefers-reduced-motion: no-preference)`.

## 7. Anti-slop tells to remove

- Purple/indigo gradients and glassmorphism "AI dashboard" look → one flat accent.
- Emoji used as functional icons → use a consistent text/SVG icon treatment.
- Everything centered; inconsistent off-scale spacing; 4+ accent colors competing.
- Heavy zebra striping + heavy borders + drop shadows all at once → pick one.
- Skeletons that never resolve; missing empty/error states; truncation with no way
  to see the full value.

## 8. How to apply (workflow)

1. Read the target component(s) and the existing styles/tokens.
2. If no token file exists, create one (Section 2) and migrate the worst offenders.
3. Fix in priority order: **hierarchy/alignment → spacing scale → status color
   consistency → state coverage → motion polish.**
4. Change source files; don't add dependencies. Verify in the running app
   (FastAPI + React dev server) — check a real incident view, an empty state, and
   reduced-motion. Share a screenshot of before/after.

## 9. Optional upgrade path (ONLY if the user confirms installs are allowed)

If the environment permits npm packages, the highest-leverage additions for an
internal MS-context tool are: **Fluent UI** (`@fluentui/react-components`) for a
native-feeling component system, or **Tailwind v4** for token-driven styling, and
**`motion/react`** for state transitions. These are enhancements, not requirements —
the guidance above stands on plain React + CSS alone.

---
*Lineage: principles mined and re-tuned for internal data dashboards from
[taste-skill](https://github.com/Leonxlnx/taste-skill) (marketing-page-oriented);
stripped of its required npm stack and re-aimed at a no-install ops cockpit.*
