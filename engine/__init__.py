"""incident-investigator-kit engine -- zero-dependency, standard library only.

Modules:
    hypothesis    -- form / rank / challenge(falsify) / prune / confidence (the brain)
    gates         -- evidence gate, falsification gate, gap marker, draft-only (the restraint)
    loop_control  -- bounded termination, stall detection, reflexion pivot (knowing when to stop)
    router        -- symptom -> query plan (no fake autonomy)
    timeline      -- correlation timeline from raw query outputs
    ui_scan       -- static UI/UX bug scanner for the UI skills (React + FastAPI)

The loop is built against the three failure modes research finds in LLM root-cause
agents (stalling, confirmation bias, confusion): evidence-grounding + a mandatory
falsification step + bounded loops with a forced reflexion pivot. Iterating harder
does not help; attacking your own leading hypothesis does.

See demo.py for a full mock investigation, and CLAUDE.md for office adoption.
"""
