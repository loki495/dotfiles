Discover and inventory every feature/subsystem in the current project's codebase (frontend and
backend) as a Format v2 atlas, then — only once that inventory is done and confirmed — offer to
also audit it for what's worth fixing. Designed to be re-run repeatedly as the project changes: it
only refreshes what actually changed.

Split into two phases on purpose: **Phase A (Inventory)** always runs and just records what's
there. **Phase B (Audit)** is offered, not automatic, after Phase A finishes.

**Arguments:** $ARGUMENTS

- No argument: incremental update mode (default) — only new/changed/removed subsystems get
  refreshed.
- `full`: treat every subsystem as stale and re-read all of them.
- `audit`: skip the Phase A/B offer and run both phases straight through.

## Where the atlas lives

**Dibs mode** (the `dibs` MCP, or the `todo:agent:*` CLI fallback, is reachable): the atlas is a
Format v2 parent issue `Feature atlas: <Project>` — labels `research` and `feature atlas`, in the
project's own Group, no parent issue — plus one comment per subsystem, edited in place with
`todo_comment` `commentId` + `expectedRevision`. Find atlases with `todo_list` label `feature
atlas`; when a parent lacks that label, add it with `todo_revise` `addLabels`. Revise the parent
body WITHOUT `todo_revise`'s `note` (each note becomes a comment in the atlas thread; consumers use
the comment ids from the index). The format and the Refresh procedure are
defined in the mapper and scout agent docs.

**File mode** (Dibs unreachable — say so to the user): `.ai/feature-atlas/INDEX.md` holds the
parent body and `.ai/feature-atlas/<id>.md` each subsystem comment, with the same fields. Audit
output is `AUDIT-<id>.md` per subsystem and `REPORT.md`.

The atlas describes the code at its recorded SHA, the commit last verified, which may be local
and unpushed. Refresh the touched subsystems after every commit (`/feature-atlas-subsystem`), on
whichever branch the work is committed; pushing or opening a PR is optional. Entries for unmerged
work are provisional: if the branch is dropped, re-verify at the default branch tip. After history
surgery or a rebase merge changes SHAs, re-stamp to the resulting SHA. Dibs's local database is
authoritative; before working on a repo, compare its GitHub tip (the atlas's branch on `origin`)
with the atlas's Verified at and, if GitHub is ahead or differs, bring the atlas up to date first.
The parent body carries a `Branch:` line naming the branch the atlas describes, default the
default branch (`main`/`master`); a branch that needs its own atlas gets a separate parent titled
`Feature atlas: <Project> [<branch>]`. It holds no findings: audit findings are ordinary Dibs
tasks.

## Findings

Findings from `/feature-atlas` audits and from `/job-search-audit` share one shape, so one
register of known problems serves both. A finding is an ordinary Dibs task in the repo's Group with
exactly one kind label: `bug` (a defect in the code), `docs drift` (a doc that disagrees with the
code or the atlas) or `portfolio` (affects only how the repo reads to an outside reader). Its body
states the repo, the atlas subsystem id, the `Verified at` SHA the evidence was checked against,
`file:line` with the quoted text, a severity and a suggested fix. Search for an open task first and
update it rather than filing a duplicate. A repo's public docs must list its open `bug` tasks as
known limitations.

## Models

Every atlas agent defaults to Sonnet: reading every owned file and writing down what it does (the
mapper, scouts and auditors) is detailed but not subtle. The synthesizer judges and rejects
auditor findings, where a false bug filed in Dibs costs more than a missed one: launch it with
`model: opus` the first time it runs on a repo, then Sonnet once its output has been spot-checked.
Calibrate occasionally by running one subsystem's scout on both models and diffing the comments;
keep the stronger model only where it finds real differences.

To save Claude tokens, any step may instead run on Codex, Antigravity's `agy` or opencode, at the
model and thinking/reasoning level that suits it, when calibration shows the result is good enough
(inventory reading and scouts are the likeliest candidates; keep judgement steps such as the
synthesizer on a strong model). Check what is installed and which models are offered rather than
guessing names; the launch commands and flags are in the `orchestrator-worker` skill's cross-tool
section. A worker that reads and writes its own comments must still read every owned file itself
(the depth rule is unchanged), and whoever launches it verifies the comments it wrote.

---

## Phase A — Inventory

1. **Confirm project root and mode** — verify there's a recognizable project here (git repo,
   `composer.json`, `package.json`, etc.); ask if ambiguous. Pick Dibs or file mode as above and
   find the project's Group (`todo_context`; ask before creating one).

2. **Detect conventions** — project type (Laravel / OpenCart / other) and the root `CLAUDE.md`.
   Pass these to every agent below.

3. **Find the atlas** — Dibs: `todo_list` label `feature atlas`, match the project; none means a
   first run. File mode: `.ai/feature-atlas/INDEX.md`.

4. **Run discovery** — run the `feature-atlas-mapper` with the project root, conventions, and the
   atlas location (or "none, first run"); with `full`, tell it to treat every subsystem as stale.
   It runs its Refresh procedure and reports: tip SHA, new / stale / removed / unchanged
   subsystems, v1 conversions (owned_paths rewritten as pathspecs), conflicts, and uncovered files.

5. **Checkpoint** — on a first-ever run, or if new+stale is more than ~8, or if there are
   conflicts, uncovered files or v1 conversions, show the plan to the user before proceeding:
   counts, the lists, and anything needing a decision. A small routine incremental update with
   none of those proceeds directly.

6. **Resolve conflicts and uncovered files** — ask how to resolve each: fold into an existing
   subsystem's `owned_paths`, mint a new subsystem, list it under Shared infrastructure or Not
   read, or flag it as dead code for a separate look. Never silently redraw a subsystem's
   boundary, reassign its files, or fold a file into a boundary it doesn't fit just to pass the
   coverage check.

7. **Scout** — for each new or stale subsystem run `feature-atlas-scout`, in the foreground:
   sequential, or at most a few in one message. Each scout reads every owned file and test body
   itself and writes one v2 comment (Dibs: edit the existing comment in place, or add a new one;
   file mode: `<id>.md`). Do not run the auditor in this phase.

8. **Collect open questions** — gather the scouts' purpose/intent questions, untested behaviour and
   doc/code drift. Don't resolve questions by guessing; hold them for the Phase A summary.

9. **Handle removed subsystems** — edit the comment to say `removed at <sha>` and drop its index
   line. In file mode keep the file.

10. **Update the parent** — Dibs: `todo_revise` the parent body (no `note`): Verified at (advances
    to the tip only when nothing is pending), Latest release, the index with current comment ids
    and ` (partial)` markers, Shared infrastructure, Not read. On a first run create the parent
    first (labels `research` + `feature atlas`, project Group, no parent issue), then add the
    comments, then fill the index. Before finishing: every `depends-on` id exists in the index, and
    the coverage diff run from the empty tree (`4b825dc642cb6eb9a060e54bf8d69288fbee4904`) to the
    tip returns nothing. File mode: write `INDEX.md`.

11. **Phase A summary + ask about Phase B** — report subsystem counts (new/stale/removed/unchanged),
    a one-line purpose per subsystem, the open questions (the answers go into the relevant
    comment), and ask whether to continue to Phase B. Stopping here is a complete outcome.
    Test gaps and doc/code drift from step 8 become one task per run in the project's Group, filed
    via the synthesizer's Dibs step (or `todo_create` directly when no audit follows); search
    first for an existing one.

## Phase B — Audit (offered, not automatic)

Only runs if the user confirmed at step 11, or `audit` was passed.

12. **Audit** — run `feature-atlas-auditor` in the foreground for every subsystem touched in Phase
    A, plus any subsystem without a current audit if the user asks. Dibs mode: the auditors return
    their findings in their responses; no `AUDIT.md`. File mode: `AUDIT-<id>.md`.

13. **Synthesize** — run `feature-atlas-synthesizer` with the findings. It re-verifies every
    finding, runs the meta-passes, and (Dibs mode) files each verified finding as a task under one
    `Feature atlas audit: <Project> <date>` parent task in the project's Group after `todo_search`
    for duplicates; file mode: `REPORT.md`.

14. **Handle newly-discovered subsystems** — for `NEW SUBSYSTEM REQUIRED` entries, resolve the
    boundary as in step 6, scout and audit them, update the parent (step 10), then re-run the
    synthesizer once. Never fold a real coverage gap into an existing boundary to avoid this.

15. **Offer the project CLAUDE.md pointer** — if the project's root `CLAUDE.md` doesn't mention
    the atlas, propose a short section: the atlas is the Dibs issue `Feature atlas: <Project>`
    (found with `todo_list` label `feature atlas`; `.ai/feature-atlas/` in file mode), and
    `/feature-atlas` should be run after adding/removing/substantially changing a feature, or
    before a refactor spanning multiple subsystems. Show the exact diff and get explicit
    confirmation before writing.

16. **Final summary** — subsystem counts, the audit parent task and its top few items, and anything
    skipped or needing a manual decision.

**Notes:**
- This command never edits project source files — only the atlas (Dibs, or `.ai/feature-atlas/`)
  and, with explicit confirmation, the project's root `CLAUDE.md`.
- No background workers: every agent runs in the foreground.
- For a single subsystem you already know, prefer `/feature-atlas-subsystem` — far cheaper.
- To re-rank an existing audit without rescanning code, use `/feature-atlas-report`.
- Repeated Phase-A-only runs are a complete workflow: refresh, removal handling and the coverage
  check all run in Phase A.
- The atlas describes **current state only** — never write "this changed since last run" or
  "previously X, now Y" into the parent or a comment. If a refresh surfaces something durable (a
  real gotcha, a reason behind a non-obvious design choice), route it to a `lesson`- or
  `research`-labeled Dibs issue per the orchestrator-worker skill; otherwise drop it.
