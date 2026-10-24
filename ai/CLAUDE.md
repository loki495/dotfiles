# Claude Code entrypoint

The rules shared by every agent (Claude Code, Codex, agy, opencode) live in `RULES.md`; this
file only adds what is specific to Claude Code. Read the shared rules first.

@RULES.md
@CLAUDE.private.md

## Context window management

Every call re-reads the whole context, so a session's size matters well before the
window is full: cache reads were ~95% of all tokens in a week-long audit (2026-10-05),
with sessions running to ~950k. Budget: once context passes **~250k tokens**, tell
Andres and offer `/handoff` then `/clear` before starting new work (finish the current
step first). Same when coming back to a session idle longer than the prompt-cache TTL
(~1h) with a large context: the next prompt rewrites the whole context at cache-write
price, so a fresh session from a hand-off is usually cheaper. Avoid `/model` switches
and plugin reloads mid-way through a big session for the same reason (each forces a
full cache rewrite); under ~50k tokens the rewrite is small and a switch is fine.

## Hooks summary (see hooks config for full detail)

**All projects:**
- Push guard (`hooks/push-guard.sh`, PreToolUse on Bash): any command containing
  `git push` (including `rtk git push` and chained commands) forces a permission prompt
  showing the exact command, whatever the permission mode or allow rules. In a repo with a
  feature atlas it first denies the push when a subsystem's owned files changed since that
  subsystem's `Verified at` (or its stamp is no longer on the branch), naming the subsystems;
  Dibs unreachable skips only that check (`hooks/atlas-helper.py`, atlas cached 5 min).
- Commit gate (`hooks/commit-gate.sh`, PreToolUse on Bash): at `git commit` it denies a message
  that says docs were updated (a `Docs: updated` line, or prose such as "README updated") when no documentation file (`.md`, `.rst`, `docs/`) is in the commit (a test file does not count); otherwise it only adds
  context: a code-only commit without docs/tests (add them or say `Docs: n/a (reason)`) and the
  atlas subsystems the commit touches (update and stamp them after committing). Commit messages
  never mention Dibs or the atlas.
- Claim overlap (`hooks/claim-overlap.sh`, PreToolUse on Edit/Write/MultiEdit/NotebookEdit):
  asks Dibs (`todo:agent:claims`, via `docker exec dibs-app`) whether the file lies inside the
  claimed `paths` of another live claim and, if so, adds a warning to the context; never blocks,
  and says so when Dibs is unreachable. Claims list their paths through `todo_claim`'s `paths`.
- Stop gate (`hooks/stop-gate.sh`, Stop): blocks ending the session while it still holds a live
  Dibs claim (`todo:agent:claims --held-by=<session id>`, via `docker exec dibs-app`), telling
  Claude to complete or release it. Blocks at most twice per session (`STOP_GATE_CAP`, counter
  in a private `dibs-stop-gate/` dir under `$XDG_RUNTIME_DIR`, else `~/.cache`), then allows with a visible warning so it never loops;
  `DIBS_STOP_GATE=off` in the environment skips it; Dibs unreachable allows with a warning.
  Subagent stops are not gated; a user interrupt or API error never reaches a Stop hook.
- Context budget (`hooks/context-budget.sh`, UserPromptSubmit): over budget (default
  250k, `CLAUDE_CTX_BUDGET`) it shows a warning and tells Claude to offer `/handoff` +
  `/clear`; after an idle gap (default 60 min, `CLAUDE_CTX_IDLE_MIN`) with context over
  `CLAUDE_CTX_IDLE_FLOOR` (default 100k) it blocks the prompt once — re-send to continue
  anyway. Slash commands always pass through.

**Laravel projects:**
- On PHP file write: Pint (auto-fix) → PHPStan level 6 (report only, must address before commit)
- Pre-commit: Pint (auto-fix, re-stage) → PHPStan level 6 (blocks on failure) → Rector
  dry-run (blocks if changes found, shows diff, never auto-applies) → Pest (blocks on
  failure; see hard rule above)

**OpenCart projects:**
- No automatic hooks. Opt-in only via project's own `.claude/project.md`.

@RTK.md
