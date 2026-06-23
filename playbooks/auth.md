# Playbook: auth

**Symptom class:** `auth`
**Triggers:** 401/403 spike, login failures, token rejections, "users can't sign in".

## Router registration
```python
register("auth", ["auth_failures_by_reason", "recent_cert_rotations", "identity_provider_health", "deploy_timeline"])
```

## Signals to gather (in order)
1. `auth_failures_by_reason` — failure reason breakdown (expired token, bad signature, unknown key, MFA).
2. `recent_cert_rotations` — cert/key/secret rotations or expiries in the window.
3. `identity_provider_health` — IdP/SSO/OAuth provider availability and latency.
4. `deploy_timeline` — auth-service or middleware deploy/config change.

## Candidate hypotheses
| Hypothesis | Prior | Confirmed by | Refuted by |
|---|---|---|---|
| Expired / rotated cert or signing key | 0.35 | failures = "bad signature"/"unknown key"; rotation ts matches | keys current |
| IdP / SSO outage | 0.30 | provider errors/timeouts, correlated | provider healthy |
| Bad auth deploy / config | 0.25 | failures start at deploy ts | failures predate deploy |
| Clock skew | 0.10 | "token not yet valid"/"expired" cluster; host time drift | clocks in sync |

## Decision notes
- "Unknown key id" right after a key rotation → rotation pushed without distributing the new public key.
- Failures cluster on **one host/pod** with time-validity errors → clock skew on that node.
- Treat all credential/secret values as sensitive — reference them by name, never echo values into the RCA.

## Output
DRAFT RCA via `templates/rca-draft.md`. Remediation suggested only.
