"""Symptom -> query router. The "no fake autonomy" gate.

The model should NOT free-guess which query to run -- that is non-reproducible
and where investigations go sideways. Instead, symptoms map deterministically to
named queries here, and your private adapter binds those names to the real
callables in your own queries.py. The public repo never sees a real query.

Adopting in your office repo (see CLAUDE.md):
    from engine.router import register, route
    import queries  # your private module
    register("latency", ["p99_by_route", "deploy_timeline", "dependency_latency"])
    bind("p99_by_route", queries.p99_by_route)   # your real callable
    ...
    plan = route("latency spike on checkout")    # -> ordered list of query names

Pure standard library. Python 3.8+.
"""
from __future__ import annotations

from typing import Callable, Dict, List

# symptom-class -> ordered list of query NAMES (strings, not callables)
_ROUTES: Dict[str, List[str]] = {}
# query name -> real callable, bound privately in your adapter
_BOUND: Dict[str, Callable] = {}

# Generic keyword -> symptom-class map. Extend for your domain in the adapter.
_KEYWORDS: Dict[str, str] = {
    "latency": "latency", "slow": "latency", "p99": "latency", "timeout": "latency",
    "down": "availability", "5xx": "availability", "unavailable": "availability",
    "error rate": "availability", "crashloop": "availability",
    "401": "auth", "403": "auth", "auth": "auth", "token": "auth", "login": "auth",
    "stale": "data-freshness", "lag": "data-freshness", "delay": "data-freshness",
    "throttl": "throttling", "429": "throttling", "rate limit": "throttling",
}


def register(symptom_class: str, query_names: List[str]) -> None:
    """Declare which queries (by name, in order) investigate a symptom class."""
    _ROUTES[symptom_class] = list(query_names)


def bind(query_name: str, fn: Callable) -> None:
    """Bind a query name to a real callable. Do this only in your private adapter."""
    _BOUND[query_name] = fn


def classify(symptom_text: str) -> str:
    """Map free-text alert/symptom -> a registered symptom class (deterministic)."""
    t = (symptom_text or "").lower()
    for kw, cls in _KEYWORDS.items():
        if kw in t:
            return cls
    return "unknown"


def route(symptom_text: str) -> List[str]:
    """Return the ordered query plan for a symptom. Empty list = unmapped: the
    agent must say so and fall back to the playbook-author skill, not improvise."""
    return list(_ROUTES.get(classify(symptom_text), []))


def run_plan(symptom_text: str) -> Dict[str, object]:
    """Execute bound queries for a symptom and return {query_name: result}.
    Skips unbound names (returns a marker) so a half-wired adapter fails loudly."""
    results: Dict[str, object] = {}
    for name in route(symptom_text):
        fn = _BOUND.get(name)
        results[name] = fn() if fn else "<UNBOUND-QUERY>"
    return results


if __name__ == "__main__":
    register("latency", ["p99_by_route", "deploy_timeline", "dependency_latency"])
    register("auth", ["auth_failures_by_region", "recent_cert_rotations"])
    bind("p99_by_route", lambda: {"p99_ms": 820, "baseline_ms": 200})

    print("classify:", classify("checkout p99 spike, timeouts"))
    print("plan:", route("checkout p99 spike, timeouts"))
    print("run:", run_plan("checkout p99 spike, timeouts"))
    print("unmapped:", route("disk smells funny"))
