Re-run just the cross-subsystem validation, meta-audit, and ranking pass for
`.claude/feature-atlas/` and rebuild `REPORT.md` — without rescanning any code. Useful after one or
more `/feature-atlas-subsystem` refreshes, or whenever the ranked TODO list needs to reflect the
latest state of the existing `DETAILS.md`/`AUDIT.md` files.

**Arguments:** $ARGUMENTS (unused)

---

**Workflow steps:**

1. **Require an existing atlas** — `.claude/feature-atlas/SUMMARY.md` must exist with at least one
   subsystem folder. If not, tell the user to run `/feature-atlas` first.

2. **Synthesize** — spawn `feature-atlas-synthesizer` against `.claude/feature-atlas/`. It
   independently re-verifies every finding against current code, rejects/narrows/demotes weak
   ones, runs the coverage/duplication/DRY/over-abstraction/schema/dependency-ranking meta-passes,
   and rewrites `REPORT.md` plus `SUMMARY.md`'s descriptive digest.

3. **Handle newly-discovered subsystems** — if it reports `NEW SUBSYSTEM REQUIRED` entries, tell
   the user: those need a full mapper-confirmed scout → auditor pass, which this lightweight
   command doesn't run. Offer to hand off to `/feature-atlas-subsystem <name>` for each one, or
   `/feature-atlas` to pick them all up along with anything else that's changed.

4. **Report** — summarize the top priority items from the rebuilt `REPORT.md` and link to it.
