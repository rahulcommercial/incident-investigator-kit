---
name: react-performance
description: >
  Make a React data dashboard fast when it renders large query results, long log
  output, and streaming agent replies — using no-install patterns (windowing,
  pagination, render hygiene), not heavy libraries. Use when the UI is janky, a
  table/log view is slow, typing lags, or a view re-renders too much. Tuned for an
  internal incident tool on React + FastAPI. Mined and re-implemented dependency-free.
---

# react-performance

Incident dashboards die on **volume**: a query returns 10k rows, a log view streams
thousands of lines, the timeline has hundreds of events, and the agent streams
tokens while all of it is mounted. This skill keeps it smooth without pulling in a
virtualization library — though it flags where one would help if installs are ever
allowed.

## Diagnose first (don't optimize blind)

1. Identify the slow surface: which component re-renders or blocks? Use React
   DevTools Profiler / `<Profiler>` if available; otherwise reason from the code.
2. Classify the cause: **too much data mounted**, **too many re-renders**, or
   **expensive work in render**. The fix differs for each — don't memoize your way
   around a 10k-row DOM.

## Pattern A — too much data mounted (the big one)

The fix is to **not render what isn't visible.**

- **Server-side pagination/slicing (preferred, zero-install).** Have FastAPI return
  a page/window (`?offset=&limit=`) and render only that. Best for query-result
  tables — the backend is already there.
- **Manual windowing (zero-install).** For long log/timeline views, render only the
  slice in the scroll viewport: track scroll offset, compute visible index range,
  render that range plus a small buffer, pad with spacer divs for correct scrollbar.
  ~30 lines, no dependency.
- **Cap + "load more".** Render the first N (e.g. 200) rows with an explicit
  "show more" — simplest, and fine for most incident views.
- *Optional (only if installs allowed):* `@tanstack/react-virtual` does windowing
  robustly. Suggest it; don't add it unilaterally.

## Pattern B — too many re-renders

- **Stable keys.** Lists keyed by a stable id (incident id, row id), never array index — index keys cause wrong reuse and re-render churn.
- **Memoize the heavy children**, not everything. `React.memo` a row/cell component so a parent state change (e.g. streaming chat) doesn't re-render the whole table.
- **Stable callbacks/values.** `useCallback`/`useMemo` for props passed to memoized children or dependency arrays — *with a real reason*; needless memoization adds cost and noise.
- **Isolate fast-changing state.** Streaming text, hover, scroll position, and a live timer should live in a small leaf component or a ref — not in a parent whose re-render cascades to the table. (Pairs with the tokens guidance: continuous values via ref/leaf state.)
- **Split context.** Don't put rapidly-changing values in a wide context provider; every consumer re-renders. Separate "slow" (theme, user) from "fast" (stream) contexts.

## Pattern C — expensive work in render

- Move filtering/sorting/formatting of large arrays into `useMemo` keyed on the data + params — not recomputed every keystroke.
- **Debounce** search/filter inputs over big datasets (~150–250ms) so each keypress doesn't re-filter 10k rows.
- Keep date/number formatting out of hot render paths (precompute, or memoize formatters).

## Streaming & async hygiene

- Append streamed tokens to an isolated leaf; don't re-render the surrounding investigation view per token.
- Cancel in-flight fetches on unmount / param change (AbortController) to avoid wasted work and state-after-unmount warnings.
- Code-split heavy, rarely-used views (`React.lazy` + `Suspense`) so the main dashboard loads fast.

## Output

Name the slow surface, the cause (A/B/C), and apply the **smallest** fix that
addresses it — usually pagination/windowing for volume, memo+key for churn. Verify
the view stays responsive with a realistically large dataset (don't test with 5
rows). Don't add a library without asking.
