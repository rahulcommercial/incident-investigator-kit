# Playbook: availability

**Symptom class:** `availability`
**Triggers:** 5xx spike, error-rate SLO burn, "service down", crashloop, health-check failures.

## Router registration
```python
register("availability", ["error_rate_by_route", "deploy_timeline", "pod_restarts", "dependency_health"])
```

## Signals to gather (in order)
1. `error_rate_by_route` — 5xx vs total; which routes/status codes; blast radius (region/AZ).
2. `deploy_timeline` — recent deploy/config/flag change before onset.
3. `pod_restarts` — crashloops, OOMKills, failed readiness probes.
4. `dependency_health` — is a downstream returning errors / refusing connections?

## Candidate hypotheses
| Hypothesis | Prior | Confirmed by | Refuted by |
|---|---|---|---|
| Bad deploy / config | 0.40 | errors start at change ts; only new build/region | errors predate change |
| Crashloop / OOM | 0.25 | restart count climbing, OOMKill events | pods stable |
| Dependency failure | 0.25 | downstream 5xx/connection refused, correlated | dependencies healthy |
| Infra / network | 0.10 | AZ-scoped, LB/DNS errors | single-service scope |

## Decision notes
- 5xx concentrated in **one region/AZ** → infra or a region-scoped rollout, not global code.
- Climbing restart count + OOMKill → memory regression in the new build.
- Connection-refused to a downstream → that dependency is the cause; pivot the investigation there.

## Output
DRAFT RCA via `templates/rca-draft.md`. Remediation suggested only.
