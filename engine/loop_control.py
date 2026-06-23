"""Bounded-loop control -- mined from agentic-sop-to-work's loop engineering.

An expert investigator stops when they've found the cause, run out of leads, or
hit a wall -- not when they get bored. This makes "stop" deterministic:

  - max_steps         : hard ceiling so the loop always terminates.
  - stall detection   : N steps with no new evidence -> stop, you're spinning.
  - coverage          : fraction of hypotheses actually tested -> are we thorough?

Pure standard library. Python 3.8+.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class LoopController:
    max_steps: int = 12          # hard ceiling on investigation steps
    stall_limit: int = 3         # consecutive no-evidence steps before we quit
    steps: int = 0
    _evidence_count_history: List[int] = field(default_factory=list)

    def tick(self, total_evidence_now: int) -> None:
        """Call once per investigation step, passing the running evidence count."""
        self.steps += 1
        self._evidence_count_history.append(total_evidence_now)

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

    def should_continue(self, open_hypotheses: int, concluded: bool) -> bool:
        if concluded:
            return False
        if open_hypotheses == 0:
            return False
        if self.steps >= self.max_steps:
            return False
        if self.stalled:
            return False
        return True

    def stop_reason(self, open_hypotheses: int, concluded: bool) -> str:
        if concluded:
            return "root cause confirmed"
        if open_hypotheses == 0:
            return "all hypotheses exhausted (no confirmed cause -- report INSUFFICIENT EVIDENCE)"
        if self.steps >= self.max_steps:
            return f"hit step ceiling ({self.max_steps}) -- escalate with current findings"
        if self.stalled:
            return f"stalled ({self.stall_limit} steps, no new evidence) -- escalate / request data"
        return "still running"


if __name__ == "__main__":
    lc = LoopController(max_steps=6, stall_limit=2)
    counts = [1, 2, 2, 2]  # evidence stops growing -> should stall
    for c in counts:
        lc.tick(c)
        print(f"step {lc.steps}: evidence={c} stalled={lc.stalled} "
              f"continue={lc.should_continue(open_hypotheses=2, concluded=False)}")
    print("STOP:", lc.stop_reason(open_hypotheses=2, concluded=False))
