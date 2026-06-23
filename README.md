# incident-investigator-kit

**A zero-dependency kit that makes an AI agent investigate incidents like a senior
SRE — hypothesis-driven, evidence-gated, and incapable of fabricating a root cause.**

Standard-library Python + markdown skills. No `pip install`, no network calls, no
external services. Built for locked-down environments where you can't add
dependencies or let data leave the box.

## Why this exists

Most "AI incident bots" do one of two things badly:

- **Free-associate a root cause** — confident, ungrounded, occasionally fabricated.
- **Need a heavy stack** — cloud SDKs, vector DBs, API keys, a Node runtime.

This kit takes the **hypothesis-driven investigation loop** (form → rank → gather
evidence → branch/prune → confidence-scored conclusion) and wraps it in
**determinism gates** (no ungrounded claims, explicit data gaps, draft-only output,
bounded loops). The model supplies judgement; the code supplies restraint.

> Synthesis of two ideas the source projects had separately and neither had
> together, dependency-free: the hypothesis loop (à la RunbookAI) and SOP-to-work
> determinism gates (à la agentic-sop-to-work).

## What's inside

```
engine/            # 5 stdlib modules — the actual machinery
  hypothesis.py    #   form / rank / branch / prune / confidence  (the brain)
  gates.py         #   evidence gate · gap marker · draft-only     (the restraint)
  loop_control.py  #   bounded termination · stall · coverage      (when to stop)
  router.py        #   symptom -> query plan                       (no fake autonomy)
  timeline.py      #   raw query output -> correlation timeline
  ui_scan.py       #   static UI/UX bug scanner (React + FastAPI)   (the UI skills' teeth)
  demo.py          #   full mock investigation — run it, see it work
skills/            # drop-in agent skills (SKILL.md each)
  investigate/         run a disciplined investigation
  playbook-author/     turn a TSG/SOP into a deterministic playbook
  investigation-audit/ read-only: did the agent stay honest?
  internal-ui-taste/      make the React dashboard sharp & dense (no-install, CSS-only)
  ui-design-review/       read-only critic: grade a view against internal-ui-taste
  ui-accessibility-audit/ WCAG 2.2 AA keyboard/ARIA/contrast audit (no axe-core)
  react-component-patterns/ composition, kill prop-soup, clean state architecture
  react-performance/      windowing/pagination + render hygiene for big data views
playbooks/         # generic starting playbooks: latency, availability, auth, data-freshness
templates/         # blank playbook + DRAFT RCA templates
CLAUDE.md          # how to adopt this in a PRIVATE repo (no egress, no deps)
```

## Try it in 10 seconds

```bash
python -m engine.demo
```

You'll watch it route a latency symptom to a query plan, build a timeline, spot the
suspect deploy, test three competing hypotheses, confirm one with cited evidence,
refuse to guess about a missing host metric (`<NEEDS-DATA>`), and emit a DRAFT RCA
that flags its one unverified claim for human sign-off.

## The five rules it enforces in code (not vibes)

1. **No ungrounded claims.** A conclusion with no cited source is rejected by the
   `evidence_gate`. Period.
2. **Gaps are marked, not filled.** Missing data becomes a `<NEEDS-DATA>` marker, a
   better answer than a confident fabrication.
3. **Output is always a DRAFT.** No "final" — only a draft a human promotes.
4. **No mutating actions.** Remediation is suggested; a human runs it.
5. **The loop terminates for a reason.** Confirmed cause, exhausted hypotheses,
   step ceiling, or stall — never an open-ended spin.

## Making the UI sharp (5 skills + a scanner)

The kit also hardens the React + FastAPI dashboard the investigator lives in — all
zero-install (plain React + CSS), tuned for a **data cockpit**, not a landing page.
They work as a loop:

```
ui-design-review   →  internal-ui-taste  →  ui-accessibility-audit
   (critique)           (apply fixes)          (verify operable)
   read-only            edits + tokens.css      WCAG 2.2 AA, keyboard
```

- **ui-design-review** (read-only) grades a view against the taste rules + `tokens.css`.
- **internal-ui-taste** applies the fixes; `tokens.css` is the copy-paste design
  foundation (spacing/type scale, status palette matching the engine states).
- **ui-accessibility-audit** verifies the result is keyboard-operable and AA-contrast.
- **react-component-patterns** / **react-performance** keep it maintainable and fast
  (composition over prop-soup; windowing/pagination for big query tables & log views).

All three review/audit skills start by running the deterministic scanner so the model
doesn't eyeball mechanical bugs:

```bash
python -m engine.ui_scan src/        # 30 React/FastAPI rules, exact file:line + fix
python -m engine.ui_scan --list-rules
```

Includes two cockpit-specific rules: **`status-color-only`** (status shown by color
with no text/label — fails colorblind users) and **`list-no-pagination`** (tables/
lists rendering rows with no windowing — the query-result and log-view jank).

> The scanner is vendored from the author's own
> [ui-ux-doctor](https://github.com/rahulcommercial/ui-ux-doctor) — same
> code-does-the-exact-work / model-does-the-judgement split as the investigation engine.

## Using it on your own incidents

The public kit is generic. To wire it to your real queries and runbooks **without
copying anything private here**, see [CLAUDE.md](CLAUDE.md): you write a small
adapter that binds the router's query *names* to your real callables, and translate
your TSGs into playbooks on your side. Names are public; code and data stay private.

## Credits / lineage

Patterns mined and re-implemented dependency-free from:
- [agentic-sop-to-work](https://github.com/s0912758806p/agentic-sop-to-work) — determinism gates, draft-only, gap-marking, loop control.
- [RunbookAI](https://github.com/Runbook-Agent/RunbookAI) — hypothesis-driven investigation loop, confidence scoring, branch/prune.

## License

MIT — see [LICENSE](LICENSE).
