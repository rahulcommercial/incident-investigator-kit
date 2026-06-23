---
name: react-component-patterns
description: >
  Keep a growing React dashboard maintainable: composition over configuration,
  compound components, killing boolean-prop soup, clean state architecture, and
  first-class loading/empty/error states. Use when a component has too many props,
  is hard to reuse, mixes data-fetching with rendering, or when adding a new view.
  React + FastAPI, zero dependencies. Mined and re-implemented dependency-free.
---

# react-component-patterns

Internal tools rot in a predictable way: one `<Panel>` grows 20 boolean props,
data-fetching tangles into JSX, and every new incident view copy-pastes the last.
This skill keeps the dashboard composable as it grows. Pure React patterns — no
libraries.

## 1. Composition over configuration

When a component sprouts flags (`isCompact`, `showHeader`, `hasFooter`,
`variantPrimary`…), stop adding props — **let callers compose**.

- **Boolean-prop soup → compound components.** Instead of `<ResultTable showToolbar
  sortable selectable dense />`, expose parts:
  ```tsx
  <ResultTable>
    <ResultTable.Toolbar />
    <ResultTable.Head sortable />
    <ResultTable.Body dense />
  </ResultTable>
  ```
  Share state via an internal context, not a dozen props. Same for `<Timeline>` /
  `<Timeline.Event>` and `<Chat>` / `<Chat.Message>` / `<Chat.ToolCall>`.
- **`children` and slot props** beat config objects for layout. Pass a node, not a
  flag that conditionally renders one.

## 2. Variants without booleans

- Replace mutually-exclusive booleans (`isCritical`, `isWarning`, `isHealthy`) with
  one `status` union: `status: 'critical' | 'warning' | 'info' | 'healthy'`. Maps
  straight to the tokens.css palette and the engine states
  (`confirmed/refuted/needs-data/open`). Illegal combinations become unrepresentable.
- A `size`/`density` union (`'compact' | 'comfortable'`) instead of `isDense`.

## 3. Separate data from presentation

- **Custom hooks own fetching.** `useIncident(id)`, `useQueryResult(name)` encapsulate
  the FastAPI call, loading/error state, and cancellation; the component just renders
  what the hook returns. Swappable, testable, no fetch logic in JSX.
- **Presentational components take data as props** and stay dumb — easy to reuse
  across the dashboard and the RCA draft view.

## 4. State architecture

- **Local first.** Keep state in the smallest component that needs it. Lift only when
  two siblings truly share it.
- **`useReducer` for multi-field flows** (the investigation/filter panel) instead of
  five entangled `useState`s — transitions become explicit and reviewable.
- **Context for cross-cutting, slow-changing values** (theme, current user, selected
  incident). Keep fast-changing values (stream text, hover) OUT of wide context — see
  the react-performance skill.
- Derive, don't duplicate: compute values during render from source state instead of
  syncing copies with effects.

## 5. State coverage is part of the component, not an afterthought

Every data component handles four outcomes explicitly (mirrors internal-ui-taste):
`loading` (skeleton/context) · `empty` (message + next action) · `error` (surface the
FastAPI detail + retry) · `success`. A standard `<AsyncBoundary>` wrapper or a
`status` switch keeps this consistent across views.

## 6. Resilience

- **Error boundaries** around independent regions (timeline, table, chat) so one
  failing panel doesn't blank the whole investigation view.
- Keep components pure: no side effects in render; effects are for syncing with the
  outside world, with correct dependency arrays and cleanup.

## Output

Refactor toward composition incrementally — collapse the worst prop-soup or
fetch-in-JSX component first, prove the pattern, then apply it to siblings. Don't
introduce a state-management library; these patterns cover an internal dashboard's
needs with plain React.
