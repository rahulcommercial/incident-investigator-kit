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
    CONFIRMED = "confirmed"  # evidence crossed the confirm threshold
    REFUTED = "refuted"      # evidence dropped it below the prune floor
    NEEDS_DATA = "needs_data"  # cannot progress without a signal we don't have


# Evidence weights. Positive supports the hypothesis, negative refutes it.
# Kept coarse on purpose -- an expert reasons in "strong/weak", not 0.731.
SUPPORT_STRONG = 0.35
SUPPORT_WEAK = 0.15
REFUTE_WEAK = -0.20
REFUTE_STRONG = -0.45

CONFIRM_AT = 0.85   # confidence at/above this -> CONFIRMED
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

    def mark_needs_data(self, what: str) -> "Hypothesis":
        """Use when a hypothesis cannot move without a signal you don't have.
        This is the honest alternative to guessing -- see gates.mark_gap."""
        self.evidence.append(Evidence(source="(none)", detail=f"NEEDS: {what}", weight=0.0))
        self.status = Status.NEEDS_DATA
        return self

    def _reclassify(self) -> None:
        c = self.confidence
        if c >= CONFIRM_AT:
            self.status = Status.CONFIRMED
        elif c <= PRUNE_BELOW:
            self.status = Status.REFUTED
        else:
            self.status = Status.OPEN


def rank(hypotheses: List[Hypothesis]) -> List[Hypothesis]:
    """Open hypotheses, highest confidence first -- the next thing to test."""
    return sorted(
        (h for h in hypotheses if h.status == Status.OPEN),
        key=lambda h: h.confidence,
        reverse=True,
    )


def branch(parent: Hypothesis, sub_statements: List[str]) -> List[Hypothesis]:
    """Strong evidence -> drill down. Children inherit a slice of the parent's
    confidence as their prior so the search stays focused on the live lead."""
    seed = round(parent.confidence * 0.6, 3)
    return [Hypothesis(statement=s, prior=seed, parent_id=parent.id) for s in sub_statements]


def prune(hypotheses: List[Hypothesis]) -> List[Hypothesis]:
    """Drop refuted leads; return what's still worth pursuing or concluding."""
    return [h for h in hypotheses if h.status != Status.REFUTED]


def conclusion(hypotheses: List[Hypothesis]) -> Optional[Hypothesis]:
    """The confirmed hypothesis, if any. None means: not enough evidence yet --
    report that honestly rather than inventing a cause."""
    confirmed = [h for h in hypotheses if h.status == Status.CONFIRMED]
    return max(confirmed, key=lambda h: h.confidence) if confirmed else None


if __name__ == "__main__":
    # Self-test: a deploy-regression beats a noisy-neighbour theory.
    pool = [
        Hypothesis("Latency caused by bad deploy at 14:02", prior=0.4),
        Hypothesis("Latency caused by noisy neighbour", prior=0.3),
        Hypothesis("Latency caused by upstream dependency", prior=0.3),
    ]
    pool[0].add_evidence("queries.deploys", "deploy 14:02 precedes p99 spike 14:03", SUPPORT_STRONG)
    pool[0].add_evidence("queries.p99", "p99 4x baseline only on new build", SUPPORT_STRONG)
    pool[1].add_evidence("queries.host_cpu", "neighbour CPU flat", REFUTE_STRONG)
    pool[2].mark_needs_data("upstream dependency latency metric")

    for h in rank(pool):
        print(f"[{h.confidence:.2f}] {h.status.value:9} {h.statement}")
    win = conclusion(pool)
    print("CONCLUSION:", win.statement if win else "INSUFFICIENT EVIDENCE")
