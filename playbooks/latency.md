# Playbook: latency

**Symptom class:** `latency`
**Triggers:** p99/p95 spike, timeouts, "slow", SLO burn on latency.

## Router registration
```python
register("latency", ["p99_by_route", "deploy_timeline", "dependency_latency", "host_saturation"])
```

## Signals to gather (in order)
1. `p99_by_route` — confirm the spike, isolate the affected route(s) and magnitude vs baseline.
2. `deploy_timeline` — any deploy/rollout/flag change in the 30 min before onset?
3. `dependency_latency` — are upstreams (DB, cache, downstream services) slow, or healthy?
4. `host_saturation` — CPU/memory/connection-pool saturation on the serving fleet.

## Candidate hypotheses
| Hypothesis | Prior | Confirmed by | Refuted by |
|---|---|---|---|
| Bad deploy / rollout | 0.40 | spike starts at deploy ts; only on new build | spike predates deploy |
| Upstream dependency slow | 0.30 | upstream p99 elevated, correlated | upstreams at baseline |
| Capacity / saturation | 0.20 | host CPU/pool maxed; scales with traffic | resources healthy |
| Noisy data / false alert | 0.10 | metric artefact, no user impact | real user errors present |

## Decision notes
- Latency that appears **exactly** at a deploy ts and only on the new build → deploy is prime suspect; suggest rollback (do not execute).
- Latency that scales with traffic and shows resource saturation → capacity, not code.
- If no host/saturation query exists yet: `<NEEDS-DATA> host_saturation: needs per-host CPU + pool metrics`.

## Output
DRAFT RCA via `templates/rca-draft.md`. Remediation suggested only.
