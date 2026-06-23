"""incident-investigator-kit engine -- zero-dependency, standard library only.

Modules:
    hypothesis    -- form / rank / branch / prune / confidence (the brain)
    gates         -- evidence gate, gap marker, draft-only output (the restraint)
    loop_control  -- bounded termination, stall detection, coverage (knowing when to stop)
    router        -- symptom -> query plan (no fake autonomy)
    timeline      -- correlation timeline from raw query outputs
    ui_scan       -- static UI/UX bug scanner for the UI skills (React + FastAPI)

See demo.py for a full mock investigation, and CLAUDE.md for office adoption.
"""
