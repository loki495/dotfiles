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

After the checks (not on `--dry-run`) it also runs the rules export below with `--commit` semantics:
the export files are rewritten when the rule records changed and committed (just those paths, never
pushed). Rule validation problems (exit 3 of the export) appear in the standing issue under "Rule
export problems", not as "Dibs unreachable".

Tests: `python3 -I tests/test_dibs_reconcile.py` (fixture git repo, fake Dibs: violation present,
second run, violation cleared, dry run, Dibs unreachable).

## token-usage.py

Report-only token usage from Claude transcripts under `~/.claude/projects` (stdlib Python 3):

```bash
python3 ~/dotfiles/ai/scripts/token-usage.py [--days 28] [--ctx-limit 250000] [--projects-dir DIR] [--budget 10 20]
```

Per day and per ISO week: sessions, API turns (deduped by message id, subagent transcripts
included), total tokens, tokens per session, cache-read share, the share of turns whose context
was over `--ctx-limit` (the context-budget target), a change-vs-previous-week column on the weekly table, and a bar scaled to the busiest bucket. A `cost$` column estimates the API-list-price equivalent
(per-model rates in `PRICES`, 5 minute cache writes at 1.25x, unknown models cost 0), and a footer
estimates how long each `--budget` (USD, default 10 and 20) of prepaid API credit would last at the
average spend per active day.

Tests: `python3 -I tests/test_token_usage.py`.

## rules-export.py

Exports the open Dibs issues labelled `rule` to files agents read: `ai/rules.md` (public) and
`~/.dotfiles-private/ai/rules.private.md` (records also labelled `private`; never in the public
file). Each rule is a `## <id>@<revision> <title>` heading and its text (the record body up to the
first `Trigger:`/`Check:`/`Applies to:`/`Source:`/`Merged candidates:`/`Always:`/`Keys:`/`Pull when:`
line). Ordered by id, so the output is stable and a file is rewritten only when it changed.

Tiers: every rule has exactly one label, `tier always`, `tier trigger` or `tier pull`, and the metadata
lines go at the end of the body. `tier always` needs `Always: <one line>`, `tier trigger` needs
`Keys: k1, k2` (known keys only, see `KEYS` in the script), `tier pull` needs `Pull when: <text>`. From
these the export writes:

- between `<!-- rules-export:start -->` and `<!-- rules-export:end -->` in `ai/RULES.md` (public rules)
  and `~/.dotfiles-private/ai/CLAUDE.private.md` (private rules): the always lines, then a rule index
  (`- <id> [<keys>] <title>` or `- <id> [pull: <when>] <title>`, no revisions). Text outside the
  markers is never touched; a missing or repeated marker is an error.
- `ai/rules-triggers.json` and `~/.dotfiles-private/ai/rules-triggers.private.json`: `{key: [rule ids]}`
  for the `rule-inject` hook.

If any rule fails validation (wrong tier labels, missing line, unknown key) none of these four files is
written, each problem is reported, and `rules.md` is still exported (a rule is never dropped).

```bash
python3 ~/dotfiles/ai/scripts/rules-export.py [--public PATH] [--private PATH] [--rules-md PATH] \
    [--private-md PATH] [--triggers PATH] [--private-triggers PATH] [--commit | --check]
```

`--commit` commits just the changed paths in their own repo; it never pushes. A `RULES.md` or private
markdown file that already has uncommitted changes is neither rewritten nor committed that run (it is
retried next time), so a session's unfinished edit is not committed as "Rules export". `--check`
renders everything, writes nothing and lists the files that differ. Exit codes: 0 ok, 1 `--check` found
drift, 2 Dibs unreachable (nothing written), 3 validation or marker problems (printed to stderr). The
reconciler runs the export hourly. The `rule-inject` hook and the other agents read these files, never
Dibs.

Tests: `python3 -I tests/test_rules_export.py`.

## lessons-export.py

Exports the active lesson records to the cache the `rule-inject` hook's lesson channel reads
(`~/.cache/dibs-lessons.json`, `LESSON_CACHE` overrides). A lesson is active when it is open, labelled
`lesson`, not labelled `draft`, and has at least one `trigger <key>` label (see the Dibs guide on lesson
records). Per lesson the cache keeps id, triggers, group and area, and from the body the `Summary:`,
`Hits:` and `Last seen:` values; a lesson without a `Summary:` line is skipped. The Dibs command prefix
is `DIBS_CLI` (default `docker exec -u www-data dibs-app php artisan`); the script runs `todo:agent:list
--knowledge` once and `todo:agent:show` per active lesson. If the list call or any show call fails, the old
cache stays and the exit code is 2. A lock file stops two runs overlapping. The hook starts this
script detached when the cache is missing or older than `LESSON_TTL` seconds (default 3600); run it by hand to refresh at once.

Tests: `python3 -m unittest tests.test_lessons_export`.

## curator.py

The unattended Dibs curator. A systemd timer starts one pass; the script decides whether
it may run, launches a fresh agent session bound to Dibs, and keeps the bookkeeping. It never asks
questions: anything that needs Andres becomes a proposal.

```bash
python3 ~/dotfiles/ai/scripts/curator.py gate --pass light [--json]   # read-only: would it run now?
python3 ~/dotfiles/ai/scripts/curator.py run --pass light --dry-run   # gate, candidate, command and prompt; writes nothing
python3 ~/dotfiles/ai/scripts/curator.py run --pass light             # what the timer runs
```

Units: `curator@.service` runs `curator.py run --pass %i` under
`env -i HOME PATH` (rule 1225); `curator-light.timer` starts `curator@light` hourly with up to 10
minutes of random delay, `curator-heavy.timer` starts `curator@heavy` at 02:30 (`Persistent=true`).
`curator-heavy.timer` is enabled (tracked wants link); the light timer is not, so its hourly runs
start only after `systemctl --user enable --now curator-light.timer`.

Configuration lives in `ai/curator/`:

- `curator.conf`: `ACTIVE_MIN` (minutes of quiet needed), `ACTIVITY_PATHS` (transcript roots whose file
  mtimes count as activity), the quota probe model and timeout, claim heartbeat, run log retention,
  and the Dibs area and group of the standing issues.
- `candidates.txt`: `tier agent profile model effort`, cheapest suitable first. Only `claude` has a
  launcher today; other agents are skipped as `no adapter`.
- `base.md`: the unattended preamble every pass prompt starts with (no questions, proposal format,
  authority limits, stop-safe items, a short summary at the end).
- `passes/<name>.md`: `Key: value` headers (`Tier`, `Timeout-min`, `Budget-usd`, `Min-interval-min`,
  `Tools`, `Precheck`), a `---` line, then the prompt body. Placeholders: `{run_id}`, `{pass}`,
  `{runs_issue}`, `{proposals_issue}`, `{last_ok}`, `{model}`. `light.md` and `heavy.md` are
  read-only placeholders until the light pass (lesson curation, dropped-task consolidation) and the
  heavy pass (Dibs cleanup, stale atlas refresh) replace their bodies. `Tools` may add only
  `Read`, `Grep` or `Glob` scoped to an absolute path under `TOOL_PATHS` (curator.conf, default
  `~/www:~/dotfiles`), written `Read(//home/andres/www/**)` and also passed as `--add-dir`, or single
  Dibs tools; anything else is a configuration error. `Precheck` is a command whose exit 1 means
  "nothing to do", so no model starts.

The gate, in order: the lock `~/.local/state/curator/curator.lock` (it records the holder's pid,
start and deadline; a holder past its own deadline whose process is still that curator run is
terminated, per skill resource-cleanup), the pass's minimum interval,
`sessioneer --list` (any session not `idle` or `blocked` blocks; sessions tagged `curator` or named
`[curator]...` are ignored), recent transcript activity, the precheck, then the first candidate of
the pass tier whose live profile quota is below `QUOTA_GO_MAX` from skill session-flow
`thresholds.conf`. With no candidate the run parks and exits 0. Anything that cannot be read counts
as "do not run".

The quota comes from a probe, because the stored Sessioneer reading goes stale while no session runs:
one `claude -p` call per candidate profile with `PROBE_MODEL` (no tools, no MCP, no persisted session,
budget $0.05) whose `rate_limit_event` gives the five-hour and seven-day use. A probe can start a new
five-hour window. A failed probe, an unreadable event or pay-as-you-go overage parks the run. `gate`
and `--dry-run` never probe: they name the first candidate of the tier without checking its quota.

A run then makes sure the standing issues `Curator runs` and `Curator proposals` exist (label
`curator`), claims `Curator runs`, snapshots the records labelled `rule`, and starts
`claude -p --restricted --tools "" --strict-mcp-config --mcp-config <dibs only> --permission-mode
dontAsk --no-session-persistence` with the candidate's model and effort. The agent can use only the
Dibs tools (plus the pass's scoped read tools): it cannot run commands, push, edit files or config, or
reach Sessioneer. Sessions are not persisted, so curator runs never count as activity. While it runs
the script checks the model of the init event and of every assistant message against the requested
one (a launcher can silently ignore `--model`; no init event means "model not verified"), stops the agent at `QUOTA_PARK` (read from the run's own `rate_limit_event` lines), at the pass
timeout, or on a model mismatch,
heartbeats the claim, and copies the stream-json output to `~/.local/state/curator/runs/<run id>.jsonl` (stderr to
`<run id>.stderr`). A SIGTERM from systemd (stop or `TimeoutStartSec`) ends the run the same way:
the agent's process group is killed and the report and release still happen.
Afterwards a changed `rule` record marks the run not ok (tool rules cannot block a Dibs edit, so it is
detected instead). One report comment goes on `Curator runs` (outcome, model verified, cost, quota
before and after, other models in the usage totals, pass summary), the claim is released on every path, and
`~/.local/state/curator/last-<pass>.json` records the outcome. Exit codes: 0 ok, skipped or parked;
2 configuration or Dibs error; 3 run not ok.

Proposals are child tasks of `Curator proposals`: title `Proposal: <decision>`, label `proposal`,
body lines `Question:`, `Options:` (recommended first), `Evidence:`, `Key:`; idempotency key
`curator:proposal:<key>`; none are filed past 75 open children. An interactive curator run, started
by hand, answers them.

Tests: `python3 -I tests/test_curator.py` (fake Sessioneer, Dibs CLI and claude; about a minute).
