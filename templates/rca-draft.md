# DRAFT — RCA: <incident id / title>

> This is a DRAFT produced by an agent. A human must review and approve before
> any mutating action. Unverified claims and data gaps are listed at the bottom.

## Summary
<one-paragraph plain-language summary: what broke, who/what was impacted, and the
current best root-cause hypothesis with its confidence (e.g. "85% confident">.

## Impact
- **What:** <symptom — latency / errors / staleness>
- **Scope:** <routes / regions / % of traffic / users>
- **Window:** <start ts> → <end / ongoing> (source: <query>)

## Timeline
| Time | Event | Source |
|---|---|---|
| <ts> | <deploy / flag / config change> | <query> |
| <ts> | <first alert / symptom onset> | <query> |
| <ts> | <key observation> | <query> |

## Root cause (confidence: <NN>%)
<the confirmed hypothesis, with the ≥2 independent evidence items that support it,
each cited. If nothing reached the confirm threshold, write: **INSUFFICIENT
EVIDENCE** and list exactly what data would settle it.>

## Ruled out
- <hypothesis> — refuted by <evidence> (source: <query>)

## Suggested remediation (NOT executed)
1. <step> — <expected effect> — <how to verify>
2. <rollback / mitigation> — requires human approval to run.

## Unverified claims (need confirmation before action)
- <claim that is plausible but not yet evidence-backed>

## Open data gaps
- `<NEEDS-DATA> <field>: needs <signal/query>`

## Sign-off
- [ ] Reviewed by: __________   Date: ______
- [ ] Approved to action remediation
