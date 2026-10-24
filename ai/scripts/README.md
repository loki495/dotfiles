# ai/scripts

## dibs-measure.py

Report-only measurement of how well the Dibs workflow is followed. Always exits 0; stdlib
Python 3. Run it from any shell:

```bash
python3 ~/dotfiles/ai/scripts/dibs-measure.py [--days 30] [--until 2026-10-21T23:59:59]
```

It prints a table and a `summary:` line per measure:

1. **Atlas drift.** Every open Dibs issue labelled `feature atlas` is read for its `Repo:`,
   `Branch:` and `Verified at:` lines and compared with the branch tip (local and `origin/`):
   commits behind and files changed since the stamp. A stamp that is not an ancestor of the
   branch (history rewrite) shows as `stamp NOT on branch`; one the repo does not have as
   `stamp unknown to repo`.
2. **Push vs atlas.** Claude transcripts under `~/.claude/projects/-home-andres-www-personal-*`
   modified in the last `--days` days: per project dir, sessions that ran `git push`, and how
   many of those edited an atlas (`todo_comment`/`todo_revise` containing `Verified at`) after
   the first push. `--until` ignores activity after that time, so a past window can be
   re-measured. Malformed or truncated transcript lines are skipped.
3. **Dead claims.** Open tasks whose claim is no longer alive (a session ended holding it).
   Closed tasks with no commit SHA in the closing note and the Dibs activity log cannot be read:
   the `todo:agent:*` CLI lists open tasks only, so that line says `n/a`.

Dibs is read through `docker compose exec ... php artisan todo:agent:*` in `$DIBS_DIR`
(default `~/www/personal/dibs`); if that fails the script says so on stderr and reports what
it can. For offline runs and tests, `--atlas-json` / `--claims-json` take saved JSON,
`--projects-dir` points at other transcripts, `--skip-dibs` skips Dibs.

Tests: `python3 tests/test_dibs_measure.py` (fixture transcripts, a throwaway git repo).

## dibs-reconcile.py

Mechanical invariant check, run hourly by `dibs-reconcile.timer` (no model session; never pushes
and never leaves the host). It lives in dotfiles, not Sessioneer, because it is a Dibs/git
hygiene job that must work whichever agent ran last and needs only git, docker and the Dibs CLI.
Reuses `dibs-measure.py` for atlas drift and dead claims.

Checks: atlas `Verified at` vs the branch tip (the freshest of the local and `origin/` refs, so a
stale local ref is not a rewrite; a stamp no tip has is `unverifiable`), claims whose owner is
dead, plans whose body never mentions a closed step (`S<n>` or `#id`), and closed plan steps whose
closing note has no commit SHA (only steps closed since `RECONCILER_SINCE`, default `2026-10-24`,
when the completion guards landed).

Output: one standing issue `Reconciler findings` (Personal Projects, group `AI workflows`,
label `reconciler`), whose body is rewritten only when the findings changed. An unverifiable atlas
stamp, or an atlas at least `RECONCILER_BEHIND_TASK` (default 3) commits behind, also gets one
child task with a `Key:` line and idempotency key `reconciler:atlas:<name>:<stamp>`; the task is
closed when the stamp is current or changed. At most `RECONCILER_MAX_TASKS` (default 10, `--max-tasks`) violation tasks are open at once; an existing task keeps its slot, and violations past the cap are only listed in the standing issue ("N more violations not filed as tasks"), which bounds the damage of a bad read (for example every atlas looking unverifiable). `--dry-run` prints the findings and writes nothing.
If Dibs is unreachable it writes nothing and exits 2.

It does not launch repair workers. Closed tasks outside plans are not checked (the CLI lists open
tasks only).

Tests: `python3 -I tests/test_dibs_reconcile.py` (fixture git repo, fake Dibs: violation present,
second run, violation cleared, dry run, Dibs unreachable).
