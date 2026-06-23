---
name: playbook-author
description: >
  Turn a human-written TSG, SOP, or runbook into a deterministic investigation
  playbook the investigate skill can execute. Use when onboarding a new incident
  class, when a symptom routes to "unknown", or when a user wants to encode tribal
  knowledge ("here's how we debug X") into a repeatable workflow. Produces a
  playbook markdown file plus the router registration for its queries. Zero
  dependencies.
---

# playbook-author

Convert prose runbooks into structured playbooks. This is the SOP-to-work step:
the human SOP stays the source of truth, but the *routing and ordering* become
deterministic code so the investigation is reproducible, not improvised.

## Method

1. **Read the source TSG/SOP.** Identify: the symptom/trigger, the signals an
   expert checks, the order they check them, the thresholds that matter, and the
   decision branches ("if p99 only on new build → suspect deploy").
2. **Name the symptom class.** One stable key (e.g. `latency`, `auth`,
   `data-freshness`). This is what `router.classify` will map free-text alerts to.
3. **List the queries — by name, in order.** These are *names*, not code. The real
   `queries.py` callables get bound privately in your adapter (see CLAUDE.md). If a
   needed signal has no query yet, record it as a gap to build, don't invent one.
4. **Encode the decision tree as hypotheses.** Each branch in the SOP becomes a
   candidate `Hypothesis` with a prior and the evidence that confirms/refutes it.
5. **Write the playbook file** to `playbooks/<class>.md` using
   `templates/playbook.md`. Add the router registration snippet.
6. **Mark gaps explicitly.** Anything the SOP assumes but doesn't specify (a
   threshold, a query) is a `<NEEDS-DATA>` line for a human to fill — never a guess.

## Output

- `playbooks/<symptom-class>.md` — the executable playbook.
- A `register("<class>", [...query names...])` snippet for the router.
- A short list of missing queries/thresholds the SOP implied but didn't define.

## Anti-patterns (refuse these)

- Don't fabricate a threshold the SOP didn't state — mark it `<NEEDS-DATA>`.
- Don't collapse two distinct symptom classes into one playbook to "save effort"
  (this is the mega-agent decay the kit guards against — one class per playbook).
- Don't bind real query callables here; that's private adapter work, not public.
