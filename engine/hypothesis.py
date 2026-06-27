"""Hypothesis-driven investigation core.

Mined from RunbookAI's loop (form -> rank -> gather evidence -> branch/prune ->
confidence-scored root cause) and made deterministic + dependency-free.

A Hypothesis is a falsifiable statement about a root cause. Evidence raises or
lowers its confidence. The loop always works the highest-confidence *open*
hypothesis first, branches when evidence is strong, and prunes when it collapses.
Nothing here calls an LLM or the network -- the model supplies judgement by
calling these functions; the bookkeeping stays in code so it cannot be faked.

Pure standard library. Python 3.8+.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

_ids = itertools.count(1)


class Status(str, Enum):
    OPEN = "open"            # still in play, needs more evidence
    NEEDS_FALSIFICATION = "needs_falsification"  # high belief, but not yet attacked
    CONFIRMED = "confirmed"  # crossed the confirm threshold AND survived a disproof attempt
    REFUTED = "refuted"      # evidence dropped it below the prune floor
    NEEDS_DATA = "needs_data"  # cannot progress without a signal we don't have


# Evidence weights. Positive supports the hypothesis, negative refutes it.
# Kept coarse on purpose -- an expert reasons in "strong/weak", not 0.731.
SUPPORT_STRONG = 0.35
SUPPORT_WEAK = 0.15
REFUTE_WEAK = -0.20
REFUTE_STRONG = -0.45

# Surviving a deliberate attempt to disprove a hypothesis is real, but bounded,
# support -- "I tried to break it and couldn't" is informative, not conclusive.
SURVIVED_CHALLENGE = 0.10

CONFIRM_AT = 0.85   # confidence at/above this -> eligible to confirm
PRUNE_BELOW = 0.10  # confidence at/below this -> REFUTED


@dataclass
class Evidence:
    """One observation tied to a hypothesis. `source` is where it came from
    (a query name, a TSG section, a log line) so the audit trail is real."""
    source: str
    detail: str
    weight: float

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("Evidence must cite a source -- no anonymous facts.")


@dataclass
class Hypothesis:
    statement: str
    prior: float = 0.30                      # starting belief before evidence
    evidence: List[Evidence] = field(default_factory=list)
    status: Status = Status.OPEN
    falsification_attempts: int = 0          # how many times we tried to DISPROVE it
    parent_id: Optional[int] = None
    id: int = field(default_factory=lambda: next(_ids))

    @property
    def confidence(self) -> float:
        """Prior nudged by accumulated evidence, clamped to [0, 1]."""
        c = self.prior + sum(e.weight for e in self.evidence)
        return max(0.0, min(1.0, c))

    def add_evidence(self, source: str, detail: str, weight: float) -> "Hypothesis":
        self.evidence.append(Evidence(source, detail, weight))
        self._reclassify()
        return self

    def challenge(self, source: str, detail: str, survived: bool,
                  strength: str = "strong") -> "Hypothesis":
        """Active falsification -- the antidote to confirmation bias, the #1 RCA
        failure mode. Instead of gathering more *supporting* evidence, deliberately
        look for evidence that would DISPROVE this hypothesis, and record what you
        found:

            survived=False -> the disconfirming test found something -> this refutes
                              the hypothesis (REFUTE_STRONG / REFUTE_WEAK).
            survived=True  -> the test came back clean -> the hypothesis withstood
                              an honest attempt to break it (bounded positive support).

        A hypothesis can reach high confidence but it CANNOT become CONFIRMED until
        it has survived at least one challenge -- until then it sits in
        NEEDS_FALSIFICATION. This is enforced in _reclassify() and re-checked by
        gates.falsification_gate(), so the discipline cannot be skipped.

        Example -- attack the leading "bad deploy" theory:
            h.challenge("queries.p99_by_build",
                        "v411 (old build) shows the SAME p99 spike", survived=False)
            # -> the deploy is NOT the cause; this refutes it.
        """
        self.falsification_attempts += 1
        if survived:
            self.add_evidence(source, f"[falsification survived] {detail}", SURVIVED_CHALLENGE)
        else:
            weight = REFUTE_STRONG if strength == "strong" else REFUTE_WEAK
            self.add_evidence(source, f"[falsified] {detail}", weight)
        return self

    @property
    def survived_falsification(self) -> bool:
        """True only if the hypothesis was actively attacked and is still standing."""
        return self.falsification_attempts >= 1 and self.status != Status.REFUTED

    def mark_needs_data(self, what: str) -> "Hypothesis":
        """Use when a hypothesis cannot move without a signal you don't have.
        This is the honest alternative to guessing -- see gates.mark_gap."""
        self.evidence.append(Evidence(source="(none)", detail=f"NEEDS: {what}", weight=0.0))
        self.status = Status.NEEDS_DATA
        return self

    def _reclassify(self) -> None:
        c = self.confidence
        if c <= PRUNE_BELOW:
            self.status = Status.REFUTED
        elif c >= CONFIRM_AT:
            # High belief is NOT enough to confirm a root cause. A cause must first
            # survive a deliberate attempt to disprove it; an unchallenged lead
            # waits in NEEDS_FALSIFICATION (rank() still surfaces it -- as the next
            # thing to ATTACK, not to pile more support onto).
            self.status = (Status.CONFIRMED if self.falsification_attempts >= 1
                           else Status.NEEDS_FALSIFICATION)
        else:
            self.status = Status.OPEN


# Statuses that still demand action from the loop: OPEN ones need more evidence,
# NEEDS_FALSIFICATION ones need to be attacked before they can be trusted.
_ACTIONABLE = (Status.OPEN, Status.NEEDS_FALSIFICATION)


def rank(hypotheses: List[Hypothesis]) -> List[Hypothesis]:
    """Still-actionable hypotheses, highest confidence first -- the next thing to
    work. Use next_action() to see whether the top lead needs more evidence or a
    falsification attempt."""
    return sorted(
        (h for h in hypotheses if h.status in _ACTIONABLE),
        key=lambda h: h.confidence,
        reverse=True,
    )


def next_action(h: Hypothesis) -> str:
    """What the loop should do with a ranked hypothesis next."""
    if h.status == Status.NEEDS_FALSIFICATION:
        return "CHALLENGE -- try to disprove it (h.challenge(...)) before confirming"
    if h.status == Status.OPEN:
        return "GATHER -- collect more evidence for/against (h.add_evidence(...))"
    return h.status.value


def branch(parent: Hypothesis, sub_statements: List[str]) -> List[Hypothesis]:
    """Strong evidence -> drill down. Children inherit a slice of the parent's
    confidence as their prior so the search stays focused on the live lead."""
    seed = round(parent.confidence * 0.6, 3)
    return [Hypothesis(statement=s, prior=seed, parent_id=parent.id) for s in sub_statements]


def prune(hypotheses: List[Hypothesis]) -> List[Hypothesis]:
    """Drop refuted leads; return what's still worth pursuing or concluding."""
    return [h for h in hypotheses if h.status != Status.REFUTED]


def conclusion(hypotheses: List[Hypothesis]) -> Optional[Hypothesis]:
    """The confirmed hypothesis, if any. A conclusion requires both high confidence
    AND a survived falsification attempt -- so a confident-but-unchallenged lead is
    never reported as the cause. None means: not enough evidence yet (or nothing
    has been attacked) -- report that honestly rather than inventing a cause."""
    confirmed = [h for h in hypotheses
                 if h.status == Status.CONFIRMED and h.survived_falsification]
    return max(confirmed, key=lambda h: h.confidence) if confirmed else None


if __name__ == "__main__":
    # Self-test: a deploy-regression beats a noisy-neighbour theory -- but it is
    # NOT confirmed until it survives a falsification attempt.
    pool = [
        Hypothesis("Latency caused by bad deploy at 14:02", prior=0.4),
        Hypothesis("Latency caused by noisy neighbour", prior=0.3),
        Hypothesis("Latency caused by upstream dependency", prior=0.3),
    ]
    pool[0].add_evidence("queries.deploys", "deploy 14:02 precedes p99 spike 14:03", SUPPORT_STRONG)
    pool[0].add_evidence("queries.p99", "p99 4x baseline only on new build", SUPPORT_STRONG)
    pool[1].add_evidence("queries.host_cpu", "neighbour CPU flat", REFUTE_STRONG)
    pool[2].mark_needs_data("upstream dependency latency metric")

    print("Before falsification:")
    for h in rank(pool):
        print(f"  [{h.confidence:.2f}] {h.status.value:19} {h.statement}  -> {next_action(h)}")
    print("  CONCLUSION:", conclusion(pool) or "INSUFFICIENT EVIDENCE (top lead unchallenged)")

    # Attack the leading theory: does the OLD build show the spike too? It does not.
    pool[0].challenge("queries.p99_by_build",
                      "old build v411 stayed at baseline -- spike is unique to v412",
                      survived=True)

    print("\nAfter surviving falsification:")
    win = conclusion(pool)
    for h in pool:
        print(f"  [{h.confidence:.2f}] {h.status.value:19} {h.statement}")
    print("  CONCLUSION:", win.statement if win else "INSUFFICIENT EVIDENCE")
