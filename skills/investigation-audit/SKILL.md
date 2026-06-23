---
name: investigation-audit
description: >
  Read-only auditor for a completed investigation or DRAFT RCA. Use when a user
  asks "did the agent do this properly?", before promoting a draft to a real
  postmortem, or to spot-check the agent's discipline. Verifies every claim is
  sourced, gaps are marked not guessed, no mutating action was taken, and the
  loop terminated for a real reason. Makes no changes — it only reports. Zero
  dependencies.
---

# investigation-audit

A second pair of eyes that never edits — it grades the investigation against the
kit's discipline rules and reports pass/fail with line references. Mined from the
SOP kit's read-only `agentic-workflow-audit`.

## Checklist (report each as PASS / FAIL / N-A with evidence)

1. **Grounding.** Every claim in the RCA cites a source (query name, TSG section,
   log line). Flag any sentence asserting cause/effect with no citation.
2. **Honest gaps.** Unknowns are `<NEEDS-DATA>` markers, not confident filler. Flag
   any place a value *should* be unknown but reads as asserted.
3. **Draft discipline.** Output is labelled DRAFT, lists unverified claims, and
   requires sign-off. Flag any "final"/"confirmed: do X now" framing.
4. **No mutation.** Remediation is *suggested*, never executed. Flag any text
   implying the agent restarted/rolled back/deleted anything itself.
5. **Competing hypotheses.** At least two were considered; the rejected ones show
   the refuting evidence. Flag single-track investigations (confirmation bias).
6. **Clean termination.** The loop stopped for a stated reason (confirmed /
   exhausted / ceiling / stall), not mid-thought. Flag missing stop reasons.
7. **Confidence sanity.** A 100%-confidence root cause should have ≥2 independent
   strong evidence items. Flag high confidence resting on one weak signal.

## Output

A short report: overall verdict (SOUND / NEEDS-WORK / UNSOUND), the failed checks
with quoted lines, and the single highest-priority fix. Never rewrite the RCA —
hand findings back so a human (or the investigate skill) addresses them.

## Hard rule

This skill is **read-only**. If you find yourself wanting to edit the draft, stop
and report instead. Auditor and author must stay separate.
