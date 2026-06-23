"""Deterministic timeline / correlation builder.

Root cause usually hides in *ordering*: a deploy at 14:02, a p99 spike at 14:03.
Hand the model one clean, sorted timeline instead of five raw query tables and
its reasoning gets sharply better. This module does the boring, exact work
(sorting, inflection detection) so the model only does the judgement.

Pure standard library. Python 3.8+.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence


@dataclass
class Event:
    ts: datetime
    source: str          # which query / system produced it
    kind: str            # deploy | alert | metric | config_change | log ...
    detail: str

    def line(self) -> str:
        return f"{self.ts:%Y-%m-%d %H:%M:%S}  [{self.kind:<13}] {self.detail}  ({self.source})"


def build_timeline(events: Sequence[Event]) -> List[Event]:
    """Chronological merge of events from many sources."""
    return sorted(events, key=lambda e: e.ts)


def window(events: Sequence[Event], start: datetime, end: datetime) -> List[Event]:
    return [e for e in build_timeline(events) if start <= e.ts <= end]


def first_of(events: Sequence[Event], kind: str) -> Optional[Event]:
    for e in build_timeline(events):
        if e.kind == kind:
            return e
    return None


def suspect_triggers(events: Sequence[Event], symptom_kind: str = "alert") -> List[Event]:
    """Return change-type events (deploy/config_change) that occur immediately
    BEFORE the first symptom -- the usual suspects. Correlation, clearly labelled
    as correlation: the model still has to confirm causation with evidence."""
    tl = build_timeline(events)
    symptom = next((e for e in tl if e.kind == symptom_kind), None)
    if not symptom:
        return []
    change_kinds = {"deploy", "config_change", "rollout", "feature_flag"}
    return [e for e in tl if e.kind in change_kinds and e.ts <= symptom.ts]


def render(events: Sequence[Event]) -> str:
    return "\n".join(e.line() for e in build_timeline(events))


if __name__ == "__main__":
    fmt = "%Y-%m-%d %H:%M:%S"
    evs = [
        Event(datetime.strptime("2026-06-23 14:03:10", fmt), "queries.p99", "alert", "p99 > 800ms on /checkout"),
        Event(datetime.strptime("2026-06-23 14:02:01", fmt), "queries.deploys", "deploy", "checkout v412 rolled out"),
        Event(datetime.strptime("2026-06-23 13:30:00", fmt), "queries.flags", "feature_flag", "new-cache enabled 25%"),
    ]
    print(render(evs))
    print("\nSuspect triggers before first alert:")
    for e in suspect_triggers(evs):
        print(" -", e.line())
