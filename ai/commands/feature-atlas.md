Discover and inventory every feature/subsystem in the current project's codebase (frontend and
backend), keeping `.ai/feature-atlas/` as the up-to-date source of truth for what exists — then,
only once that inventory is done and confirmed, offer to also audit it for what's worth fixing.
Designed to be re-run repeatedly as the project changes — it only refreshes what actually changed.

Split into two phases on purpose: **Phase A (Inventory)** always runs and just records what's
there — this is enough on its own when you only want to know/record the feature/subsystem
breakdown without committing to a full maintainability audit. **Phase B (Audit)** is offered, not
automatic, after Phase A finishes.

**Arguments:** $ARGUMENTS

- No argument: incremental update mode (default) — only new/changed/removed subsystems get
  refreshed.
- `full`: force a full rescan of every subsystem regardless of staleness.
- `audit`: skip the Phase A/B offer and run both phases straight through without stopping at the
  checkpoint (for scripted/non-interactive re-runs where the audit is always wanted).

---

## Phase A — Inventory

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
   a report: new / stale / removed / unchanged subsystems, any boundary conflicts, and any
   **uncovered files** (real files not claimed by any subsystem's `owned_paths` — the mapper runs
   this coverage check exhaustively every time, not just when an audit is planned).

5. **Checkpoint before fanning out** — on a first-ever run, or if new+stale count is large (more
   than ~8), or if there are boundary conflicts or uncovered files, stop and show the plan to the
   user before proceeding: counts, the list of new/stale/removed subsystems, and any
   conflicts/uncovered-file findings needing a decision. For a small routine incremental update with
   no conflicts and no uncovered files, proceed directly — running `/feature-atlas` was already the
   user's decision, this is just executing it.

6. **Resolve conflicts and uncovered files** — for any boundary conflict or ambiguity the mapper
   flagged, ask the user how to resolve it (which id owns disputed paths, whether to split/merge a
   boundary). For any uncovered files, ask the user how to handle each: fold into an existing
   subsystem's `owned_paths`, mint it as its own new subsystem (goes through the normal new-subsystem
   pipeline below), mark it as shared infra intentionally excluded from the atlas, or flag as
   dead/orphaned code worth a separate look outside this command. Never silently redraw an existing
   subsystem's boundary, reassign its files to a different id, or fold an uncovered file into a
   boundary it doesn't actually fit just to make the coverage check pass.

7. **Fan out discovery-only per-subsystem work** — for each new or stale subsystem id, run
   `feature-atlas-scout` (writes `DETAILS.md`, including its purpose/intent section — see that
   agent's own doc). Do **not** run `feature-atlas-auditor` yet in this phase — auditing is Phase B,
   offered at the checkpoint below, not chained automatically. These are workers in the
   `orchestrator-worker` sense — launch each per that skill's Launching Workers mechanics for
   whichever tool is running this command (Claude Code's `Agent` tool in-process; an equivalent
   cross-tool launch for opencode/codex/agy). Multiple subsystems' scout passes can run
   concurrently — batch them (roughly 4-6 concurrent worker launches at a time, per
   orchestrator-worker's Parallel vs Sequential Workers) rather than launching dozens at once.

8. **Collect open questions** — gather any purpose/intent open questions each scout flagged in its
   final response (per subsystem id). Don't resolve these yourself by guessing — hold them for the
   end-of-phase report to the user.

9. **Handle removed subsystems** — mark them `status: removed` in `SUMMARY.md`'s registry table.
   Leave their folder in place as a historical record; only delete it if the user explicitly asks.

10. **Update SUMMARY.md's registry table** — one row per subsystem: id, name, one-line boundary,
    status, `owned_paths`, last updated, link to its `DETAILS.md` (no `AUDIT.md` link yet — that
    only exists after Phase B). The descriptive digest section below the table is written by the
    synthesizer in Phase B, so it stays as-is (or absent, on a first run) until then.

11. **Phase A summary + ask about Phase B** — unless `audit` was passed as an argument (in which
    case skip straight to Phase B below without asking), report to the user: subsystem counts
    (new/stale/removed/unchanged), the list of subsystems with a one-line purpose each, any
    scout-flagged open questions about purpose/intent (ask the user to resolve these now if
    possible — the answer can be appended to the relevant subsystem's `DETAILS.md`), and then ask
    explicitly whether to continue on to Phase B (audit) now, or stop here with the inventory
    recorded. Stopping here is a fully valid, complete outcome of this command — don't treat it as
    partial or unfinished.

## Phase B — Audit (offered, not automatic)

Only runs if the user confirmed at the step 11 checkpoint, or `audit` was passed as an argument.

12. **Fan out audits** — run `feature-atlas-auditor` (writes `AUDIT.md`, using the existing
    `DETAILS.md`) for every subsystem touched in Phase A (new or stale) *plus* any subsystem that
    already has a `DETAILS.md` but no `AUDIT.md` yet (i.e. was inventoried in a prior
    inventory-only run and never audited). Same concurrency guidance as step 7.

13. **Update the registry's `AUDIT.md` links** — patch the rows updated in step 10 to also link
    each subsystem's `AUDIT.md`.

14. **Synthesize** — run `feature-atlas-synthesizer` to independently verify every finding,
    reject/narrow/demote weak ones, run the coverage/duplication/DRY/over-abstraction/schema/
    dependency-ranking meta-passes, and write `REPORT.md` plus `SUMMARY.md`'s descriptive digest.

15. **Handle newly-discovered subsystems** — if the synthesizer reports any `NEW SUBSYSTEM
    REQUIRED` entries, resolve their boundary with the mapper's conflict-resolution logic (step 6),
    run scout → auditor for each (steps 7 and 12), update the registry (steps 10 and 13), then
    re-run the synthesizer once more. Never fold a real coverage gap into an existing subsystem's
    boundary just to avoid this loop.

16. **Offer the project CLAUDE.md pointer** — if the project's root `CLAUDE.md` doesn't already
    reference `.ai/feature-atlas/`, propose adding a short section: that it's the source of
    truth for the project's feature/subsystem inventory, and that future sessions should run
    `/feature-atlas` after adding/removing/substantially changing a feature, or at minimum before a
    refactor spanning multiple subsystems. Show the exact diff and get explicit confirmation before
    writing — this follows the same file-edit-confirmation and per-project-CLAUDE.md-maintenance
    conventions as everything else on this machine.

17. **Final summary** — report to the user: subsystem counts (new/stale/removed/unchanged), a link
    to `REPORT.md`, the top few priority items from it, and anything skipped or left needing a
    manual decision.

**Notes:**
- This command never edits project source files — only files under `.ai/feature-atlas/` and,
  with explicit confirmation, the project's root `CLAUDE.md`.
- For a single subsystem you already know the id/name of, prefer `/feature-atlas-subsystem` — it's
  far cheaper.
- To just re-rank/re-validate existing audits without rescanning code, use `/feature-atlas-report`.
- Resuming later to run Phase B on an inventory-only pass: just run `/feature-atlas` again — it'll
  see `DETAILS.md` exists but `AUDIT.md` doesn't yet for those subsystems and offer Phase B on them
  without redoing discovery/scouting (they won't be stale unless the code changed since).
- Repeated Phase-A-only runs are a complete, standalone workflow, not a degraded version of the
  full command: staleness refresh (step 7), removal handling (step 9), and the coverage check
  (mapper step 5) all run in Phase A regardless of whether Phase B ever gets invoked, so the atlas
  stays accurate — updated where code changed, marked removed where a subsystem's paths are gone —
  purely from inventory passes.
- `DETAILS.md`/`AUDIT.md`/`SUMMARY.md`/`REPORT.md` describe **current state only** — never write
  "this changed since last run" / "previously X, now Y" narrative into them (the mapper's own report
  to you is the one place commit-range/staleness facts belong, and even that's just to decide what
  to rescan). If a refresh surfaces something durable and worth remembering beyond current state — a
  real gotcha, a reason behind a non-obvious design choice — route it to `.ai/lessons/` or
  `.ai/research/` per the orchestrator-worker skill; if it's not worth that, drop it rather than
  leaving it as commentary in the atlas.
