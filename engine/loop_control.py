"""Bounded-loop control -- mined from agentic-sop-to-work's loop engineering.

An expert investigator stops when they've found the cause, run out of leads, or
hit a wall -- not when they get bored. This makes "stop" deterministic:

  - max_steps         : hard ceiling so the loop always terminates.
  - stall detection   : N steps with no new evidence -> spinning.
  - reflexion pivot   : on a stall, force ONE self-critique + fresh hypothesis
                        before giving up (mined from Reflexion, NeurIPS'23) -- because
                        research shows naive iteration reinforces the first mistake;
                        a deliberate pivot is what actually breaks the rut.
  - coverage          : fraction of hypotheses actually tested -> are we thorough?

Pure standard library. Python 3.8+.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class LoopController:
    max_steps: int = 12          # hard ceiling on investigation steps
    stall_limit: int = 3         # consecutive no-evidence steps before we call it a stall
    max_reflexions: int = 1      # forced pivots allowed before we finally give up
    steps: int = 0
    reflexions_used: int = 0
    _evidence_count_history: List[int] = field(default_factory=list)

    def tick(self, total_evidence_now: int) -> None:
        """Call once per investigation step, passing the running evidence count."""
        self.steps += 1
        self._evidence_count_history.append(total_evidence_now)

    def record_reflexion(self) -> None:
        """Call after the agent acts on stall_directive() -- i.e. it wrote a critique
        of what it had not tested and formed a fresh hypothesis. Spends one pivot
        from the reflexion budget; if the pivot then yields evidence the stall clears
        on its own, and if it doesn't the loop stops for good next check."""
        self.reflexions_used += 1

    @property
    def stalled(self) -> bool:
        """True if the last `stall_limit` steps added no new evidence."""
        h = self._evidence_count_history
        if len(h) <= self.stall_limit:
            return False
        window = h[-(self.stall_limit + 1):]
        return window[0] == window[-1]  # no growth across the window

    def coverage(self, tested: int, total: int) -> float:
        return (tested / total) if total else 1.0

    @property
    def reflexion_available(self) -> bool:
        """A stall is only terminal once the pivot budget is spent."""
        return self.reflexions_used < self.max_reflexions

    def stall_directive(self) -> str:
        """The forced self-critique to run on a stall, before escalating. Mirrors
        Reflexion: name the blind spot, then act on it -- don't just loop harder."""
        return (
            "STALL -- no new evidence recently. Run ONE reflexion pivot before stopping: "
            "(a) name the assumption you have NOT tested yet; "
            "(b) form ONE fresh hypothesis that explains the SAME evidence differently; "
            "(c) if you genuinely cannot, stop and escalate with current findings. "
            "Then call record_reflexion()."
        )

    def should_continue(self, open_hypotheses: int, concluded: bool) -> bool:
        if concluded:
            return False
        if open_hypotheses == 0:
            return False
        if self.steps >= self.max_steps:
            return False
        if self.stalled:
            # Don't quit on the first stall -- spend a reflexion pivot first.
            return self.reflexion_available
        return True

    def stop_reason(self, open_hypotheses: int, concluded: bool) -> str:
        if concluded:
            return "root cause confirmed (survived falsification)"
        if open_hypotheses == 0:
            return "all hypotheses exhausted (no confirmed cause -- report INSUFFICIENT EVIDENCE)"
        if self.steps >= self.max_steps:
            return f"hit step ceiling ({self.max_steps}) -- escalate with current findings"
        if self.stalled and self.reflexion_available:
            return "stalled -- run a reflexion pivot (see stall_directive) before escalating"
        if self.stalled:
            return f"stalled ({self.stall_limit} steps, pivot spent) -- escalate / request data"
        return "still running"


if __name__ == "__main__":
    lc = LoopController(max_steps=8, stall_limit=2)
    counts = [1, 2, 2, 2]  # evidence stops growing -> should stall
    for c in counts:
        lc.tick(c)
        print(f"step {lc.steps}: evidence={c} stalled={lc.stalled} "
              f"continue={lc.should_continue(open_hypotheses=2, concluded=False)}")

    # First stall is not terminal -- it buys a reflexion pivot.
    print("STOP REASON:", lc.stop_reason(open_hypotheses=2, concluded=False))
    print("DIRECTIVE:", lc.stall_directive())
    lc.record_reflexion()  # agent named its blind spot and formed a new hypothesis...

    lc.tick(2)  # ...but the pivot still found nothing new -> now we stop for good
    print(f"\nafter pivot: continue={lc.should_continue(open_hypotheses=2, concluded=False)}")
    print("STOP REASON:", lc.stop_reason(open_hypotheses=2, concluded=False))
