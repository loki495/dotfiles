Refresh a single feature/subsystem's entry in `.claude/feature-atlas/` — cheap, targeted version of
`/feature-atlas` for when you already know which subsystem changed (e.g. right after implementing
or reviewing a feature) instead of rescanning the whole codebase.

**Arguments:** $ARGUMENTS — a subsystem id or a free-text name/description (e.g. `billing` or
"the notification preferences feature").

---

**Workflow steps:**

1. **Require an existing atlas** — `.claude/feature-atlas/SUMMARY.md` must already exist. If it
   doesn't, tell the user to run `/feature-atlas` first; this command only refreshes an existing
   entry or adds one alongside an existing registry, it doesn't bootstrap the whole thing.

2. **Resolve the subsystem** — match $ARGUMENTS against `SUMMARY.md`'s registry (exact id, then
   fuzzy match against names/boundary descriptions). If ambiguous between two or more, ask. If
   nothing matches, confirm with the user that this is genuinely a *new* subsystem (not a rename of
   an existing one they meant) before proceeding — and check its proposed `owned_paths` don't
   overlap an existing subsystem's before minting a new id.

3. **Staleness check** — same logic as the mapper, scoped to just this one id: git commit-range
   diff against `last_scanned_commit` (or content-hash comparison if not a git repo). If unchanged,
   tell the user and ask whether to force a refresh anyway rather than doing it silently.

4. **Refresh** — run `feature-atlas-scout` (writes/updates this id's `DETAILS.md`) then
   `feature-atlas-auditor` (writes/updates its `AUDIT.md`). If new, first draft a boundary
   description and `owned_paths` yourself (grounded in a quick look at the relevant code) since
   there's no mapper pass in this targeted flow — confirm the boundary with the user before scout
   writes anything.

5. **Patch the registry** — update only this id's row in `SUMMARY.md`'s table; leave every other
   row untouched.

6. **Flag report staleness** — `REPORT.md`'s cross-subsystem ranking now doesn't reflect this
   subsystem's latest findings. Tell the user and offer to run `/feature-atlas-report` now.
