# CLAUDE.md — adopting incident-investigator-kit in a private repo

This file tells an AI coding agent (Claude Code or similar) how to wire this
public, generic kit to a **private** incident-investigation codebase **without
copying anything internal into this repo and without adding any dependency.**

The public kit knows *how to investigate*. Your private repo knows *what to query*.
The only bridge is a small adapter you write on your side. Nothing flows back here.

## Ground rules (do not violate)

- **No dependencies.** Standard library only. No `pip install`, no network calls
  added to the engine, no external services. This is a hard constraint of the
  target environment.
- **No data egress.** Query results, TSG contents, incident details, hostnames,
  and secrets never leave the private environment and never get written into this
  public repo.
- **Names, not code, are public.** The router uses query *names* (strings). The
  real callables live only in your private adapter.

## One-time wiring (in your PRIVATE repo)

1. **Vendor the engine.** Copy the `engine/` folder (5 stdlib modules) into your
   private project, or add this repo as a path import. No install step.

2. **Write a private adapter** `incident_adapter.py` that binds router names to
   your real `queries.py` callables and registers your symptom classes:

   ```python
   from engine.router import register, bind
   import queries  # YOUR private module of kusto-backed functions

   # 1. declare symptom -> ordered query names (mirror your playbooks/)
   register("latency",      ["p99_by_route", "deploy_timeline", "dependency_latency"])
   register("availability", ["error_rate_by_route", "deploy_timeline", "pod_restarts"])
   register("auth",         ["auth_failures_by_reason", "recent_cert_rotations"])
   # ...one register() per playbook you keep

   # 2. bind each name to the real callable (PRIVATE — never in the public repo)
   bind("p99_by_route",      queries.p99_by_route)
   bind("deploy_timeline",   queries.deploy_timeline)
   bind("dependency_latency",queries.dependency_latency)
   # ...
   ```

3. **Point retrieval at your TSGs.** Your existing TSG/runbook retrieval (e.g. the
   graph-RAG you already run) supplies the `source` strings the gates require.
   When the investigate skill needs a TSG fact, it cites the TSG section name.

4. **Translate your real runbooks into playbooks.** For each incident class you
   handle, run the **playbook-author** skill against the private TSG to produce a
   `playbooks/<class>.md` *in your private repo* (not here). Start with your 3–5
   most frequent incident types; add more as they recur. One class per playbook.

## Per-incident flow (what the agent does at runtime)

1. User reports a symptom / an alert fires → **investigate** skill.
2. `router.classify` + `route` → ordered query plan (or `unknown` → playbook-author).
3. Run bound queries → build `timeline` → inspect `suspect_triggers`.
4. Form 2–4 `Hypothesis` objects → test highest-confidence first → branch/prune.
5. **Falsify before you conclude.** When the leading hypothesis reaches high
   confidence it enters `NEEDS_FALSIFICATION` — it is *not* a conclusion yet.
   Call `h.challenge(source, detail, survived=...)`: deliberately run the query
   that would *disprove* it (e.g. "did the previous build spike too?"). Only a
   hypothesis that has survived ≥1 challenge can become `CONFIRMED`. This is the
   single guard against the most common failure — confidently confirming the first
   guess. `next_action(h)` tells you whether the top lead needs evidence or a challenge.
6. Missing signal → `mark_gap`, never a guess.
7. `LoopController` decides when to stop. On a **stall** it does not quit
   immediately — `stall_directive()` forces one reflexion pivot (name the untested
   assumption, form one fresh hypothesis); call `record_reflexion()` after. Then it
   stops. Report the stop reason.
8. Emit a **DRAFT** RCA via `gates.draft_guard`, after `gates.falsification_gate(
   cause, attempts)` confirms the cause was actually attacked → human signs off →
   human (not the agent) runs any remediation.

## Verifying the wiring

```bash
python -m engine.demo      # runs the full loop on fake queries — proves zero-dep
python -m engine.router    # confirm classify()/route() see your registered classes
```

If `run_plan(...)` returns `<UNBOUND-QUERY>`, a name in `register()` has no
matching `bind()` — fix the adapter, don't work around it.

## What NOT to do

- Don't hardcode thresholds the TSG didn't state — mark them `<NEEDS-DATA>`.
- Don't let the agent execute mutating actions (rollback/restart/delete). Suggest only.
- Don't merge two symptom classes into one playbook to save effort.
- Don't copy private query bodies, TSG text, or incident data into this repo.
