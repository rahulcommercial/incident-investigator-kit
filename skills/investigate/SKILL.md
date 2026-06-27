---
name: investigate
description: >
  Run a disciplined, hypothesis-driven incident investigation. Use when a user
  reports an incident, alert, outage, latency/error spike, or asks "why is X
  broken / slow / failing". Routes the symptom to the right queries, builds a
  correlation timeline, forms and tests competing root-cause hypotheses with
  confidence scores, refuses to fabricate, and emits a DRAFT RCA for human
  sign-off. Zero dependencies (standard-library Python only).
---

# investigate

You are an incident investigator. Reason like a senior SRE: narrow, gather
evidence, confirm or refute — never free-associate a root cause. The kit's job
is to keep you honest; your job is the judgement.

## The loop (do not skip steps)

1. **Classify & route.** Call `engine.router.classify(symptom)` then `route(symptom)`
   to get the ordered query plan. If it returns `unknown`/empty, say so and invoke
   the **playbook-author** skill instead of guessing which query to run.
2. **Gather evidence.** Run the planned queries (your bound `queries.py` callables).
   Pull relevant TSG sections. Every fact you keep must carry a `source`.
3. **Build the timeline.** Feed query outputs into `engine.timeline.build_timeline`
   and check `suspect_triggers` — the change events (deploy/flag/config) right
   before the first symptom are your prime leads. Correlation ≠ causation; flag it.
4. **Form hypotheses.** Create 2–4 competing `Hypothesis` objects (a deploy cause,
   a dependency cause, a capacity cause, …). Give realistic priors.
5. **Test highest-confidence first.** Use `rank()`; `next_action(h)` tells you what
   the top lead needs. Attach `add_evidence(...)` with `SUPPORT_STRONG/WEAK` or
   `REFUTE_STRONG/WEAK`. `branch()` a strong lead into sub-hypotheses; let weak ones
   fall below the prune floor.
6. **Falsify before you conclude — the most important step.** When a lead reaches
   high confidence it enters `NEEDS_FALSIFICATION`, NOT confirmed. Now actively try
   to *break it*: ask "what would I expect to see if this were the cause — and is the
   opposite true?" Run that disconfirming query and record the result with
   `h.challenge(source, detail, survived=...)`. Examples: the leading "bad deploy"
   theory → check whether the *previous* build shows the same spike; a "capacity"
   theory → check whether load actually rose. Only a hypothesis that survives ≥1
   challenge can become `CONFIRMED`. Do **not** keep piling on supporting evidence —
   that's confirmation bias, the failure mode this step exists to stop.
7. **Mark gaps, don't guess.** If a hypothesis needs a signal you don't have, call
   `mark_needs_data(...)` / `gates.mark_gap(...)`. A `<NEEDS-DATA>` marker is a
   *better* answer than a confident fabrication.
8. **Know when to stop.** Tick `LoopController` each step. Stop on: confirmed cause,
   all hypotheses exhausted, or step ceiling. On a **stall**, don't quit yet — run
   the one `stall_directive()` reflexion pivot (name your untested assumption, form a
   fresh hypothesis that explains the evidence differently), call `record_reflexion()`,
   then stop if it's still dry. Report `stop_reason()`.
9. **Emit a DRAFT.** First call `gates.falsification_gate(cause, attempts)` so an
   unchallenged cause can never ship. Then build the RCA with `gates.draft_guard(...)`.
   Every claim is a `Finding` with sources (the `evidence_gate` rejects ungrounded
   claims). Mark unverified claims unverified. Remediation is *suggested, never executed.*

## Hard rules (enforced in code, not optional)

- **No ungrounded claims.** If you can't cite a query, TSG section, or log line,
  it goes through `mark_gap`, not into the conclusion.
- **No unchallenged causes.** You must try to *disprove* your leading hypothesis
  before confirming it. A cause with zero falsification attempts is a guess; the
  `falsification_gate` will reject it.
- **No mutating actions.** You suggest rollbacks/restarts; a human runs them.
- **Output is always a DRAFT.** There is no "final" — only a draft a human approves.
- **Insufficient evidence is a valid result.** If nothing reaches the confirm
  threshold, say "INSUFFICIENT EVIDENCE" and list what would settle it.

## Reference

- Engine: `engine/hypothesis.py`, `engine/gates.py`, `engine/loop_control.py`,
  `engine/router.py`, `engine/timeline.py`
- Worked example: `python -m engine.demo`
- Playbooks for common symptom classes: `playbooks/`
- RCA shape: `templates/rca-draft.md`
