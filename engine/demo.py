"""End-to-end mock investigation -- proves the whole engine runs with zero deps.

Run:  python -m engine.demo   (from the repo root)

This uses fake in-memory "queries" so it runs anywhere. In your office repo you
bind router query-names to your real queries.py callables (see CLAUDE.md); the
investigation loop below does not change at all.
"""
from __future__ import annotations

from datetime import datetime

from .gates import Finding, draft_guard, falsification_gate, mark_gap
from .hypothesis import (SUPPORT_STRONG, SUPPORT_WEAK, REFUTE_STRONG, Hypothesis,
                         conclusion, next_action, rank)
from .loop_control import LoopController
from .router import bind, register, route, run_plan
from .timeline import Event, build_timeline, suspect_triggers

FMT = "%Y-%m-%d %H:%M:%S"


def _fake_p99():
    return {"p99_ms": 840, "baseline_ms": 210, "route": "/checkout"}


def _fake_deploys():
    return [{"ts": "2026-06-23 14:02:01", "service": "checkout", "build": "v412"}]


def _fake_dep_latency():
    return {"upstream": "payments", "p99_ms": 190, "baseline_ms": 200}  # normal


def _fake_p99_by_build():
    # The falsification probe: did the OLD build spike too? It did not -> the
    # deploy hypothesis survives the attempt to break it.
    return {"v412": {"p99_ms": 840}, "v411": {"p99_ms": 205}}  # spike unique to v412


def main() -> None:
    # 1. Wire the router (in production this binding lives in your private adapter).
    register("latency", ["p99_by_route", "deploy_timeline", "dependency_latency"])
    bind("p99_by_route", _fake_p99)
    bind("deploy_timeline", _fake_deploys)
    bind("dependency_latency", _fake_dep_latency)
    bind("p99_by_build", _fake_p99_by_build)

    symptom = "p99 latency spike on /checkout, timeouts"
    print(f"SYMPTOM: {symptom}")
    print("QUERY PLAN:", route(symptom), "\n")
    data = run_plan(symptom)

    # 2. Build the correlation timeline from query output.
    events = [
        Event(datetime.strptime("2026-06-23 14:03:10", FMT), "queries.p99", "alert", "p99 840ms vs 210ms baseline"),
        Event(datetime.strptime(data["deploy_timeline"][0]["ts"], FMT), "queries.deploys", "deploy", "checkout v412"),
    ]
    print("TIMELINE:")
    print("\n".join(e.line() for e in build_timeline(events)))
    print("SUSPECT TRIGGERS:", [e.detail for e in suspect_triggers(events)], "\n")

    # 3. Form hypotheses and run the bounded loop.
    pool = [
        Hypothesis("Bad deploy v412 caused the latency", prior=0.4),
        Hypothesis("Upstream dependency degraded", prior=0.3),
        Hypothesis("Noisy-neighbour / host contention", prior=0.3),
    ]
    lc = LoopController(max_steps=8, stall_limit=3)

    # step: deploy hypothesis -- timeline correlation + p99 only on new build
    pool[0].add_evidence("queries.deploys", "deploy 14:02 precedes alert 14:03", SUPPORT_STRONG)
    pool[0].add_evidence("queries.p99", "840ms vs 210ms baseline on /checkout", SUPPORT_STRONG)
    pool[0].add_evidence("timeline", "no other change in the window", SUPPORT_WEAK)
    lc.tick(sum(len(h.evidence) for h in pool))

    # step: dependency hypothesis -- refuted, upstream is healthy
    pool[1].add_evidence("queries.dependency_latency", "payments p99 190ms (normal)", REFUTE_STRONG)
    lc.tick(sum(len(h.evidence) for h in pool))

    # step: noisy-neighbour -- we have no host metric; be honest, don't guess
    pool[2].mark_needs_data("per-host CPU/steal-time for the checkout fleet")
    lc.tick(sum(len(h.evidence) for h in pool))

    # The deploy lead is now high-confidence but UNCHALLENGED -- it sits in
    # NEEDS_FALSIFICATION, and conclusion() refuses to confirm it yet.
    print("HYPOTHESIS RANKING (actionable, best first):")
    for h in rank(pool):
        print(f"  [{h.confidence:.2f}] {h.status.value:19} {h.statement}")
        print(f"        next: {next_action(h)}")
    print("  conclusion before falsification:",
          conclusion(pool) or "INSUFFICIENT EVIDENCE (top lead not yet attacked)")

    # step: ATTACK the leading theory -- would the old build have spiked too?
    builds = _fake_p99_by_build()
    pool[0].challenge(
        "queries.p99_by_build",
        f"old build v411 p99 {builds['v411']['p99_ms']}ms (baseline) -- spike unique to v412",
        survived=True,
    )
    lc.tick(sum(len(h.evidence) for h in pool))

    win = conclusion(pool)
    print("\nAfter falsification -> conclusion:",
          f"[{win.confidence:.0%}] {win.statement}" if win else "INSUFFICIENT EVIDENCE")
    print("STOP REASON:", lc.stop_reason(len(rank(pool)), concluded=bool(win)), "\n")

    # 4. Emit a DRAFT RCA -- gated, gap-marked, sign-off required.
    # The falsification gate refuses to let an unchallenged cause reach the draft.
    if win:
        falsification_gate(win.statement, win.falsification_attempts)
    body = "\n".join([
        f"Root cause (confidence {win.confidence:.0%}): {win.statement}." if win else "Root cause: <unconfirmed>.",
        "Trigger: checkout deploy v412 at 14:02:01 (queries.deploys), alert at 14:03:10 (queries.p99).",
        "Ruled out: upstream payments dependency -- p99 190ms, normal (queries.dependency_latency).",
        "Survived falsification: old build v411 stayed at baseline (queries.p99_by_build) -- spike is unique to v412.",
        mark_gap("noisy_neighbour", "per-host CPU/steal-time for the checkout fleet"),
        "Suggested next step (NOT executed): roll back checkout to v411 and re-measure p99.",
    ])
    findings = [
        Finding("p99 840ms vs 210ms baseline on /checkout", sources=["queries.p99"], verified=True),
        Finding("deploy v412 at 14:02 precedes alert 14:03", sources=["queries.deploys", "timeline"], verified=True),
        Finding("rolling back v412 will resolve it", sources=["timeline"], verified=False),  # plausible, unconfirmed
    ]
    print(draft_guard("Latency incident INC-DEMO", body, findings).render())


if __name__ == "__main__":
    main()
