Re-validate and re-rank the project's open atlas audit findings without rescanning any code
beyond the cited evidence. Useful after one or more `/feature-atlas-subsystem` refreshes, or
whenever the ranked list needs to reflect the current state of the code.

**Arguments:** $ARGUMENTS (unused)

---

Atlas location and modes: see `/feature-atlas` ("Where the atlas lives"). Foreground only.

**Workflow steps:**

1. **Require an existing audit** — Dibs mode: the project's open `Feature atlas audit: <Project>
   <date>` parent task in its Group (`todo_search`) with open children. File mode:
   `.ai/feature-atlas/AUDIT-<id>.md` files. If none, tell the user to run `/feature-atlas` and
   accept Phase B first.

2. **Synthesize** — run `feature-atlas-synthesizer` against the parent's open children (their
   bodies are the findings). It re-verifies each against current code, closes or rewrites stale
   and rejected ones (noting why on the task), merges duplicates, re-runs the meta-passes, and
   re-ranks the list in the parent's body (`todo_revise`). File mode: rebuilds `REPORT.md`.

3. **Handle newly-discovered subsystems** — if it reports `NEW SUBSYSTEM REQUIRED`, tell the user
   those need a mapper-confirmed scout, which this command doesn't run. Offer
   `/feature-atlas-subsystem <name>` for each, or `/feature-atlas` to pick them all up.

4. **Report** — the top priority items from the re-ranked parent and its task id.
