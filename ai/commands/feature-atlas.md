Discover and audit every feature/subsystem in the current project's codebase (frontend and
backend), keeping `.ai/feature-atlas/` as the up-to-date source of truth for what exists and
what's worth fixing. Designed to be re-run repeatedly as the project changes — it only refreshes
what actually changed.

**Arguments:** $ARGUMENTS

- No argument: incremental update mode (default) — only new/changed/removed subsystems get
  refreshed.
- `full`: force a full rescan of every subsystem regardless of staleness.

---

**Workflow steps:**

1. **Confirm project root** — verify there's a recognizable project here (git repo, `composer.json`,
   `package.json`, etc.). If ambiguous, ask before proceeding.

2. **Detect conventions** — determine project type (Laravel / OpenCart / other) and read the
   project's root `CLAUDE.md` if present. This gets passed to every worker below so findings
   respect the project's actual conventions instead of generic defaults.

3. **Ensure the output folder exists** — `.ai/feature-atlas/`. If `SUMMARY.md` doesn't exist,
   this is a first run.

4. **Run discovery** — run the `feature-atlas-mapper` worker with the project root, detected
   conventions, and the existing `SUMMARY.md` content (or "none, first run"). If `full` was passed,
   tell it to treat every existing subsystem as stale regardless of its own diff check. It returns
   a report: new / stale / removed / unchanged subsystems, and any boundary conflicts.

5. **Checkpoint before fanning out** — on a first-ever run, or if new+stale count is large (more
   than ~8), or if there are boundary conflicts, stop and show the plan to the user before
   proceeding: counts, the list of new/stale/removed subsystems, and any conflicts needing a
   decision. For a small routine incremental update with no conflicts, proceed directly — running
   `/feature-atlas` was already the user's decision, this is just executing it.

6. **Resolve conflicts** — for any boundary conflict or ambiguity the mapper flagged, ask the user
   how to resolve it (which id owns disputed paths, whether to split/merge a boundary). Never
   silently redraw an existing subsystem's boundary or reassign its files to a different id.

7. **Fan out per-subsystem work** — for each new or stale subsystem id, run in sequence:
   `feature-atlas-scout` (writes `DETAILS.md`) then `feature-atlas-auditor` (writes `AUDIT.md`,
   using the DETAILS.md the scout just wrote). These are workers in the `orchestrator-worker`
   sense — launch each per that skill's Launching Workers mechanics for whichever tool is running
   this command (Claude Code's `Agent` tool in-process; an equivalent cross-tool launch for
   opencode/codex/agy). Multiple subsystems' scout→auditor pipelines can run concurrently — batch
   them (roughly 4-6 concurrent worker launches at a time, per orchestrator-worker's Parallel vs
   Sequential Workers) rather than launching dozens at once.

8. **Handle removed subsystems** — mark them `status: removed` in `SUMMARY.md`'s registry table.
   Leave their folder in place as a historical record; only delete it if the user explicitly asks.

9. **Update SUMMARY.md's registry table** — one row per subsystem: id, name, one-line boundary,
   status, `owned_paths`, last updated, links to its `DETAILS.md`/`AUDIT.md`. (The descriptive digest
   section below the table is written by the synthesizer in step 10.)

10. **Synthesize** — run `feature-atlas-synthesizer` to independently verify every finding,
    reject/narrow/demote weak ones, run the coverage/duplication/DRY/over-abstraction/schema/
    dependency-ranking meta-passes, and write `REPORT.md` plus `SUMMARY.md`'s descriptive digest.

11. **Handle newly-discovered subsystems** — if the synthesizer reports any `NEW SUBSYSTEM
    REQUIRED` entries, resolve their boundary with the mapper's conflict-resolution logic (step 6),
    run scout → auditor for each (step 7), update the registry (step 9), then re-run the
    synthesizer once more. Never fold a real coverage gap into an existing subsystem's boundary
    just to avoid this loop.

12. **Offer the project CLAUDE.md pointer** — if the project's root `CLAUDE.md` doesn't already
    reference `.ai/feature-atlas/`, propose adding a short section: that it's the source of
    truth for the project's feature/subsystem inventory, and that future sessions should run
    `/feature-atlas` after adding/removing/substantially changing a feature, or at minimum before a
    refactor spanning multiple subsystems. Show the exact diff and get explicit confirmation before
    writing — this follows the same file-edit-confirmation and per-project-CLAUDE.md-maintenance
    conventions as everything else on this machine.

13. **Final summary** — report to the user: subsystem counts (new/stale/removed/unchanged), a link
    to `REPORT.md`, the top few priority items from it, and anything skipped or left needing a
    manual decision.

**Notes:**
- This command never edits project source files — only files under `.ai/feature-atlas/` and,
  with explicit confirmation, the project's root `CLAUDE.md`.
- For a single subsystem you already know the id/name of, prefer `/feature-atlas-subsystem` — it's
  far cheaper.
- To just re-rank/re-validate existing audits without rescanning code, use `/feature-atlas-report`.
