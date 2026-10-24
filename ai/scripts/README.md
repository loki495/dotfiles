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
