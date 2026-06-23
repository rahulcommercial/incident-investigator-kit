# Playbook: <symptom-class>

**Symptom class:** `<class-key>`
**Triggers:** <alert names / phrasings that map to this class>

## Router registration
```python
register("<class-key>", ["<query_name_1>", "<query_name_2>", "<query_name_3>"])
```

## Signals to gather (in order)
1. `<query_name_1>` — <what it confirms / isolates>
2. `<query_name_2>` — <what change it looks for>
3. `<query_name_3>` — <rule-in / rule-out signal>

## Candidate hypotheses
| Hypothesis | Prior | Confirmed by | Refuted by |
|---|---|---|---|
| <cause A> | 0.40 | <strong evidence> | <refuting evidence> |
| <cause B> | 0.30 | <strong evidence> | <refuting evidence> |
| <cause C> | 0.20 | <strong evidence> | <refuting evidence> |
| <noise / false alert> | 0.10 | <artefact signature> | <real impact present> |

## Decision notes
- <branch rule: "if X only on new build → suspect deploy">
- <branch rule: "if scoped to one region → infra, not code">
- Missing signal? Record it: `<NEEDS-DATA> <query_name>: needs <what>` — do not guess.

## Output
DRAFT RCA via `templates/rca-draft.md`. Remediation suggested only.
