"""Determinism gates -- mined from agentic-sop-to-work.

The model is good at reasoning and bad at restraint. These gates are the
restraint, enforced in code so they cannot be argued away mid-conversation:

  evidence_gate       -- a conclusion with no cited source is rejected outright.
  falsification_gate  -- a root cause that was never attacked is rejected. Stops the
                         #1 RCA failure mode (confirmation bias) where the agent
                         confidently confirms its first guess without trying to
                         disprove it. Pairs with hypothesis.Hypothesis.challenge().
  mark_gap            -- the honest "I don't have this" marker (RunbookAI's NEEDS_DATA,
                         the SOP kit's 待補). Gaps are surfaced, never silently filled.
  draft_guard         -- every external-facing output is a DRAFT and must list its
                         unverified claims, so a human signs off before anyone acts.

Pure standard library. Python 3.8+.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# ASCII-safe gap marker (the SOP kit uses 待補; this travels better in logs/tickets).
GAP = "<NEEDS-DATA>"


class GateError(Exception):
    """Raised when a step tries to skip a gate. Loud on purpose."""


@dataclass
class Finding:
    """One claim the agent wants to make in its output."""
    claim: str
    sources: List[str] = field(default_factory=list)  # query names / TSG refs / log lines
    verified: bool = False

    def is_grounded(self) -> bool:
        return bool(self.sources)


def evidence_gate(finding: Finding) -> Finding:
    """Block any claim that cites no source. This is the single most important
    line in the kit: it is what stops the agent from fabricating a root cause."""
    if not finding.is_grounded():
        raise GateError(
            f"UNGROUNDED CLAIM rejected: {finding.claim!r}. "
            f"Attach a source (query name, TSG section, or log line) or mark_gap()."
        )
    return finding


def falsification_gate(claim: str, falsification_attempts: int) -> None:
    """Block a root-cause conclusion that was never actively challenged.

    Pass the leading hypothesis's `falsification_attempts` count. Zero attempts
    means the agent reached a conclusion without ever trying to disprove it -- the
    classic confirmation-bias trap where iterating only *reinforces* the first
    guess. Surviving a real attempt to break it is what earns the right to confirm.

    Decoupled from the hypothesis module on purpose (gates take primitives): call
    it with `conclusion.falsification_attempts` just before you emit the draft.
    """
    if falsification_attempts < 1:
        raise GateError(
            f"UNFALSIFIED root cause rejected: {claim!r}. "
            f"Actively try to DISPROVE it (Hypothesis.challenge(...)) before "
            f"concluding -- an unchallenged cause is a guess, not a finding."
        )


def mark_gap(field_name: str, what_is_needed: str) -> str:
    """Return a standardised gap string instead of a guess.

    Use everywhere a value is unknown:
        rca["root_cause"] = mark_gap("root_cause", "DB slow-query log for 14:00-14:10")
    A reader (or the audit skill) can grep for <NEEDS-DATA> to see exactly what
    blocked the investigation."""
    return f"{GAP} {field_name}: needs {what_is_needed}"


def has_gaps(text: str) -> bool:
    return GAP in (text or "")


@dataclass
class Draft:
    """Wraps any user-facing output. There is no `final` -- only a draft a human
    promotes. Mirrors the SOP kit's 'all outputs are DRAFTs' rule."""
    title: str
    body: str
    findings: List[Finding] = field(default_factory=list)

    def render(self) -> str:
        unverified = [f.claim for f in self.findings if not f.verified]
        gaps = [ln for ln in self.body.splitlines() if has_gaps(ln)]
        out = [f"# DRAFT -- {self.title}", "", self.body.strip(), ""]
        out.append("## Confidence & sign-off")
        out.append(f"- Findings: {len(self.findings)}  |  unverified: {len(unverified)}  |  open gaps: {len(gaps)}")
        if unverified:
            out.append("- Unverified claims (need human confirmation before action):")
            out += [f"    - {c}" for c in unverified]
        if gaps:
            out.append("- Open data gaps:")
            out += [f"    - {g.strip()}" for g in gaps]
        out.append("")
        out.append("> This is a DRAFT. A human must approve before any mutating action.")
        return "\n".join(out)


def draft_guard(title: str, body: str, findings: Optional[List[Finding]] = None) -> Draft:
    """Enforce: every cited finding passes the evidence gate before the draft renders."""
    findings = findings or []
    for f in findings:
        evidence_gate(f)
    return Draft(title=title, body=body, findings=findings)


if __name__ == "__main__":
    grounded = Finding("p99 spiked 4x at 14:03", sources=["queries.p99"])
    evidence_gate(grounded)  # passes

    rca_body = "\n".join([
        "Trigger: deploy 14:02 (queries.deploys).",
        mark_gap("blast_radius", "per-region error counts 14:00-14:30"),
    ])
    print(draft_guard("Latency incident INC-123", rca_body, [grounded]).render())

    try:
        evidence_gate(Finding("it was probably DNS"))
    except GateError as e:
        print("\nGATE FIRED ->", e)

    falsification_gate("deploy v412 caused it", falsification_attempts=1)  # passes
    try:
        falsification_gate("deploy v412 caused it", falsification_attempts=0)
    except GateError as e:
        print("\nGATE FIRED ->", e)
