# Playbook: data-freshness

**Symptom class:** `data-freshness`
**Triggers:** stale dashboards, pipeline lag, "data is old", SLA on freshness breached, missing recent rows.

## Router registration
```python
register("data-freshness", ["pipeline_lag_by_stage", "job_run_history", "source_volume", "downstream_consumer_lag"])
```

## Signals to gather (in order)
1. `pipeline_lag_by_stage` — where is the lag? Ingest, transform, load, or serving?
2. `job_run_history` — last successful run per stage; failures, retries, duration creep.
3. `source_volume` — did upstream volume spike (backlog) or drop to zero (no input)?
4. `downstream_consumer_lag` — is the consumer behind (e.g. Kafka/queue lag), not the producer?

## Candidate hypotheses
| Hypothesis | Prior | Confirmed by | Refuted by |
|---|---|---|---|
| Stuck / failed job | 0.35 | last success old; errors/retries in run history | jobs succeeding on time |
| Volume backlog | 0.25 | source volume spike; duration creep; lag grows with input | volume normal |
| No input (upstream dry) | 0.20 | source volume ~0; upstream incident | source flowing |
| Consumer lag | 0.20 | queue/offset lag high; producer healthy | consumer caught up |

## Decision notes
- Lag that **grows steadily** with stable volume → a stage got slower (resource/regression), not a spike.
- Last successful run is old but no errors → job is silently stuck (locked, waiting on a dependency) — check `<NEEDS-DATA> job_lock_state` if no query exists.
- Producer healthy but consumer offset far behind → the problem is downstream, pivot there.

## Output
DRAFT RCA via `templates/rca-draft.md`. Remediation suggested only.
