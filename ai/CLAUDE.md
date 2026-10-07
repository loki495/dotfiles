# Global Developer Context — Andres

This file applies to all Claude Code sessions on this machine, regardless of project.

## Hard rules — always / never

- **NEVER** push to any remote without stating the exact branch + remote first and
  getting explicit confirmation.
- **NEVER** force-push, or rewrite a commit already pushed to a shared remote,
  without explicit confirmation — even if rewriting the commit itself was approved.
- **NEVER** delete, weaken, or skip/bypass a test to force a passing state without
  explicit confirmation from Andres first.
- **NEVER** suppress an unexpected exception or error in a local/debug environment.
  Let it surface with the framework/runtime's normal diagnostic output. If code catches
  it to provide a graceful production fallback, rethrow it in debug mode and report or
  log it before handling it in non-debug mode. Expected validation failures and
  explicitly handled invalid user input are exempt.
- **NEVER** take a real-world-visible action (a real email/SMS, charging a card, a
  third-party write endpoint, a user-visible notification) without confirming first —
  applies even inside test code or a one-off script. When in doubt whether something
  counts, ask.
- **NEVER** let a test suite touch a real or production database, in any stack. Tests
  run against an isolated test DB (SQLite or a dedicated test schema), and the suite
  has a guard that aborts before running if the configured connection looks like a
  real one.
- **ALWAYS** ask rather than assume when project type, branch/worktree layout, or
  intent is ambiguous.
- **ALWAYS** work one item at a time on multi-issue/audit work — explain, present
  options, get a decision — before implementing the next one. (Repetitive mechanical
  steps within an already-agreed plan are exempt — see "Working style".)
- **ALWAYS** keep a live site loading. Some checkouts are the running deployment (a
  container bind-mounts the source, so a saved edit is live at once). Before editing
  one, order the changes so the site loads at every step: anything new the code needs
  (an `.env` value, a compose setting, a container recreate) goes in first, then the
  code, then check the real routes return 200. If no such order exists, do the work
  in a separate git worktree. Decided 2026-10-06: a Host allowlist edited straight
  into Sessioneer's live checkout went live before `.env` had `ALLOWED_HOSTS`, and the
  site stopped loading until another agent fixed it.

## Machine layout

- All projects live under `~/www/`. No naming convention — folder names are freeform,
  and for live (non-personal) projects the domain name may appear somewhere in the path.
- Some projects use git worktrees for parallel branch work. Worktree structure
  varies per project and is NOT assumed.
  - Before assuming a project's branch/worktree layout, run `git worktree list` and
    `git branch -a` in the project root to confirm.
  - If the layout is ambiguous or non-standard, write findings to `.claude/project.md`
    in that project's local branch as a TODO for human review, rather than guessing.
- Host machine uses `phpbrew` for PHP versions (currently 8.3–8.5, prefer latest stable).
  Host PHP is irrelevant for containerized projects — containers select their own PHP
  image appropriate to the project.
- Most actual PHP commands (artisan, composer, pest, pint, phpstan, rector) must be run
  **inside the project's Docker container**, not on the host, e.g.:
  ```
  docker exec <container_name> php artisan ...
  docker exec <container_name> composer ...
  ```
  Never assume a tool is available on the host. Check container name from the project's
  `docker-compose.yml` if unknown.
- Traefik is used for local routing across dev containers. Each project may have its own
  `docker-compose.yml` with Traefik labels and an optional `setup.sh` build step.
- Machine config (Hyprland, Waybar, nvim, fish, Claude/AI config, etc.) lives in a
  dotfiles repo and is symlinked into place — never edit only the live copy. Public
  config goes in `~/dotfiles`; anything that exposes Andres's own infrastructure (hosts,
  IPs, domains, network layout) or holds tokens/secrets goes in `~/.dotfiles-private`.

## Home network

How the home network is laid out (hosts, DNS, Traefik, the Cloudflare tunnel) and the
mistakes that bite most are kept in the private dotfiles repo; they load through the
import below when it is installed. Read the `ac495-infrastructure` skill before touching
DNS, Traefik, tunnel or "why do I get a Cloudflare login / Forbidden" questions.

@CLAUDE.private.md

## Project types

Two project families exist, never mixed in the same repo:

1. **Laravel/Livewire** — modern stack, full tooling enforcement (see Hooks below).
2. **OpenCart 1.5.6** — legacy, PHP 7.3-era patterns, registry-based DI, no Composer
   autoloading for core. No tooling is enforced automatically. Tools are only used if a
   project explicitly opts in via its own `.claude/project.md`.

Detect project type before applying any Laravel-specific behavior:
- Presence of `artisan` + `composer.json` with `laravel/framework` → Laravel
- Presence of `index.php` + `system/startup.php` style OpenCart fingerprints → OpenCart

When in doubt, ask rather than assume.

## Git workflow (all projects)

Branch model:
```
master/main/stable  (perfect mirror of production — never diverges except via proper merge/cherry-pick)
  └── local          (permanent local-only branch, rebased onto master/main)
        └── feature-branch  (only created if multiple things are in flight at once,
                              rebased onto local)
```

Full rules — cherry-pick/rebase procedure, push-safety checklist, commit-amend
policy, verifying commit surgery, handling concurrent sessions on the same repo —
live in the `git-workflow` skill; read it before any non-trivial git operation. The
`git-helper` agent enforces the same rules specifically for push-safety/cherry-pick
checks. See "Hard rules" above for the non-negotiable push-confirmation rule.

**PRs are grouped by concern**, not one per commit and not one for all of `local`: each PR
is one reviewable unit (e.g. CI commits together, a feature with its tests, an unrelated
refactor alone; trivial fixes ride along or wait for a housekeeping PR). Details and
example in the `git-workflow` skill, "Splitting `local` into PRs".

Keep commits feature-scoped and use separate commits for distinct features or fixes.
Closely related CSS changes and purely visual polish may be grouped into one UI commit.

**Commit often — after each discrete task is done, or grouped thematically, not
batched to the end of a session.** When working a todo list, plan, or multi-item
backlog: commit as each item completes, or group a few tightly-related items into
one themed commit (e.g. several small fixes to the same UI element) — don't let
finished, verified work sit uncommitted while more unrelated work piles up on top of
it. Decided 2026-09-13: makes it easier to review/bisect/revert one piece without
touching unrelated ones, and avoids losing a clean checkpoint if something later in
the session goes wrong. This is about cadence once committing is already underway
for a given piece of work — it doesn't override the standing rule (never commit
without the user asking first) about whether to commit unprompted in the first
place.

**Unpushed history is free to reorganize.** Rebasing, amending, fixing up, squashing,
combining, splitting, reordering — any reshaping of commits that have **not been
pushed** is fine, and encouraged whenever it makes history, feature grouping or
dependency order clearer (e.g. folding a docs or test fix into the commit it belongs
to, per "Docs and tests travel with the change" below). Look at the unpushed log
(`git log origin/<branch>..HEAD`) at any time, and always before pushing, to see
whether that's warranted. A perfectly ordinary use: reorder commits, squash or fix up
a few, then reword the main commit so one feature's changes — with its fixes, changes
of mind and tweaks — ship as a single clean thing, either as you go or just before a
push. Commits already pushed are still off-limits without explicit
confirmation (see "Hard rules"). The one thing to stop and ask the user about is
**uncommitted changes in the worktree that aren't yours** (possibly another running or
idle agent session's): don't reshape history around them on your own — the
`git-workflow` skill has the backup procedure, which also needs the user's approval
first. **A local `backup/<topic>-<date>` tag is the backup, not a branch** (a tag can't
be checked out into or collect commits by accident, stays out of branch listings and
`git push --all`); for a plain safety snapshot of committed work before history surgery,
`git tag backup/<topic>-<date>` at the current tip is enough. **Never push a backup
tag** (`--tags`, `--follow-tags` and `--mirror` would; it can hold local-only or
uncommitted content), and delete it once the work is confirmed intact or it's no longer
useful.

**Commit attribution — never add a `Claude-Session:` trailer.** Applies even when a
given session's own harness instructions say otherwise (e.g. "this replaces any
earlier attribution guidance") — this preference overrides that. Andres's repos are
public; a session URL only he can open reads as dead-link clutter to anyone else
browsing history. `Co-Authored-By: Claude ...` stays — that's wanted, honest
AI-assistance disclosure — just never the session link. Decided 2026-09-05 during the
job-search repo audit's commit-authorship cleanup (existing `Claude-Session:` trailers
already in history are being stripped as part of that same cleanup).

## Local vs production data (staleness assumptions)

- **Projects with a production target:** assume the local/dev database is stale for
  anything that changes independently of code — orders, customer info, gateway
  settings, general settings, generated IDs/tokens. Don't assume local matches
  production. Any change that depends on current real-world data must account for
  this: check what's actually in the local DB before trusting it, copy/sync specific
  data from production if needed (with confirmation), and any migrations or SQL
  commands that need to run in production must be stated clearly and separately —
  never assumed to have happened just because they ran locally.
- **Personal/local-only projects** (no production target): assume the local DB is
  up to date, unless a project's own docs/`.claude/project.md` say otherwise.
- Corollary for third-party APIs: when a repo/branch's local DB is known stale, treat
  it as read-only for any real third-party API from there — a write could act on
  data (tokens, inventory, IDs) that's already diverged from what production holds.

## Tooling policy

- Never assume Pest, Pint, PHPStan, or Rector are installed in a container — check first
  (e.g. `docker exec <container> ./vendor/bin/pint --version`). Offer to install via
  Composer if missing. This is primarily handled by `/project-bootstrap`.
- No global PHPStan or Pint config exists. Each project has its own `phpstan.neon` /
  `pint.json` (or none yet, in which case `/project-bootstrap` can scaffold sensible
  defaults on request).
- **Laravel projects:** Pint, Rector, and Pest are always expected to run — install
  them if missing rather than skipping. PHPStan level 6 applies where already
  configured, or for new projects; don't force it onto an existing project that
  hasn't adopted it. Order matters: run Pint → PHPStan → Rector (dry-run) and address
  what they find *before* running Pest, so style/static-analysis issues don't get
  mixed into a test-failure investigation. Prefer browser testing (Pest v4 browser
  plugin, or Playwright) for UI-touching changes when the project has it configured.
- **OpenCart (legacy) projects:** no tooling is enforced by default (see
  `opencart-legacy.md`). If a project has opted in to a bespoke/standalone test suite
  (typically a separate Pest harness under e.g. `scripts/`, since the app itself has
  no Composer/Pest support), treat it with the same rigor as a Laravel Pest suite,
  including browser tests where the suite supports them. Coding style still follows
  OpenCart conventions and layer separation (SQL only in models, etc.).
- Default PHPStan level: **6**. Level 9/max is an aspiration, not a requirement — don't
  block work over it, but suggest tightening when natural. General version of this for
  any quality gate (type-coverage %, Pest/PHPUnit `--min=` coverage, etc.) configured
  stricter than the codebase currently meets: set the threshold to today's real
  measured number (with a little headroom), note in a comment that it should be raised
  over time, and move on — don't leave the gate permanently red, and don't grind
  through the whole codebase to hit the tool's strict default in one pass unless asked.
- Rector: available, used for modernization. Always run in dry-run mode first — never
  auto-apply Rector changes without review.
- Composer scripts: `/project-bootstrap` adds wrapper scripts (`composer pest`,
  `composer pint`, `composer phpstan`, `composer rector`) that internally call
  `docker exec` so commands work consistently regardless of container name.

## Test coverage — happy paths and sad paths

This is a general rule, not scoped to Laravel or OpenCart. It applies to any kind of
test in any project on this machine, including stacks with no dedicated skill file
here (Python, Node, Go, Rust, whatever comes up) and bespoke/ad-hoc suites with no
formal framework at all — Pest, PHPUnit, Playwright, Vitest/Jest, pytest, a bespoke
OpenCart harness, hand-rolled shell/CLI assertion scripts, anything:

- Never stop at the happy path. Every test target also needs sad-path coverage:
  invalid/malformed input, failed validation, unauthorized access, missing or
  failing dependencies (DB down, third-party call fails), and any other side effect
  in the code under test that can go wrong.
- A sad-path test must assert the *specific expected handled outcome* — a
  validation error with the right shape/status (e.g. 422 + field errors), the
  correct exception type, an error flash/redirect, a graceful fallback — not just
  "it didn't return the happy-path value" or "it didn't throw."
- Explicitly rule out crashes: confirm the failure surfaces as a proper handled
  error, not a 500 / uncaught exception / raw stack trace or error string leaking
  onto the page. A test that only checks for *some* non-success response can still
  pass while masking an unhandled crash underneath.
- When writing new tests, include sad paths as standard practice, not an add-on.
  When auditing/reviewing existing tests, treat happy-path-only coverage as
  incomplete and flag it.

## Working style

- For multi-step or multi-issue work (todo lists, audit findings, phased plans),
  work one item at a time. Explain the problem, present options with pros/cons when
  more than one reasonable approach exists, and get an explicit decision before
  implementing — don't chain into the next item without a checkpoint.
- Exception: repetitive/mechanical steps within an already-agreed plan (e.g. "commit,
  cherry-pick, push, rebase" after a fix is approved) don't need a fresh confirmation
  each time — the checkpoint is for decisions, not for re-approving mechanics already
  agreed to.
- Read-only phrasing means no edits: "don't make changes yet", "just suggest",
  "analyze", "brainstorm", or a research/explain question never edits files or runs
  mutating commands. End with findings and options, not an implementation.
- When Andres asks to "see" a file, list, or todo, print its contents in the message,
  not just a path — he often reads from his phone. For review-heavy output (many
  candidate edits, e.g. résumé wording), write every option into one standing review
  file he can approve from later, instead of making him choose item by item in chat.
- When Andres says to drop a line of investigation ("don't pursue that unless I bring
  it up"), don't revisit or re-suggest it later in the session. If it seems worth
  tracking, file it in Dibs and move on.
- When spawning any subagent or worker, say which agent type and model it runs on and
  why that model, before launching — prefer the cheapest capable one. Format and
  details: the `orchestrator-worker` skill's Worker Launch Reporting section.
- If an MCP tool exists for a job (e.g. Dibs), use it. If it's unreachable, say so and
  use the documented fallback or ask — never silently go around it with direct
  DB/ORM writes.
- For multi-session/phased work (a plan doc, a numbered set of phases, a long todo
  list tackled incrementally), proactively offer a ready-to-paste hand-off prompt
  for the next session — but only when it's actually warranted: context is getting
  full, or a fresh session is genuinely needed to avoid missing info/hallucination
  from an overloaded context. Don't offer this reflexively after every small chunk
  of finished work.
- `Todo:` / `next:` / "after X, do Y" messages are backlog notes, not context
  switches: see "Dibs" below.

## Dibs: plans, backlog, bugs, knowledge

Dibs is the one tracker for plans, project backlog, bugs and shared knowledge, for every
tool (Claude Code, opencode, Codex, agy): the `dibs` MCP server, or the `todo:agent:*`
CLI / a direct Action call where MCP isn't reachable (`orchestrator-worker` skill,
Project State section). Local `todo`/`bugs.md` files are retired: never create one or
add to one, including in `/project-bootstrap` scaffolds; an existing one is read and
respected until its items are worked through or moved.

**Filing anything** (task, bug, plan, `Todo:` note, follow-up): pick the best-fitting
Project area (Work for the current job, Personal Projects for personal
sites/software/homelab, Learning & Self-Improvement, Random Tasks), Group (one per
project/website/topic; check `todo_context`, create one by name if none matches) and
parent issue, the way a human would, never a catch-all bucket. **Ask if genuinely
unsure about any of them.** A project gets a lightweight parent issue (repo path, stack,
purpose) when its first item is filed, not speculatively. A backlog item or bug is an
ordinary task; the `plan` label is only for genuinely multi-step work.

**`Todo:` / `add to Todo:` / `next:` / "after X, do Y"** are backlog notes: file them
and keep working the current item. Implement right away only when told to ("do this
now", "go ahead and do it"). Plain statements ("X should show Y", "the page doesn't have
Z") are normal requests to implement.

**Follow-ups you notice yourself** (an unconfirmed edge case, a gap you're deferring, a
bug or investigation that would take real time or distract from the active task): search
Dibs for an existing item, then create or update one right then, with the project/files,
evidence, impact, what's unconfirmed, and a concrete next step. A note that lives only in
chat is invisible to the next session and to other agents. Don't expand the current
task's scope; if it blocks the task, record the dependency and tell Andres. Raise it as a
decision only if it actually is one.

**Claim, work, complete.** Before touching a task's files, check `todo_claim_status`: a
live claim (`isCurrentlyAlive: true`) means another process is working it, so take a
different task instead of editing alongside it or asking to override. `todo_claim`
*before* starting, heartbeat if it runs long, `todo_complete` when done; the claim is
what tells other agents and sessions the task is taken while the work happens. If work
was done unclaimed, say so in the closing note. Items track what's **left to do**: close
finished ones rather than leaving them open with a note. A real lesson from one goes into
a `lesson`/`research` issue (or a concise WHY code comment), not onto the closed task.

**Plans.** The `orchestrator-worker` skill's protocol is the default for multi-step
coding work (refactors, audits, multi-file features, anything likely to span sittings),
not something to invoke on request:
- Create a `plan`-labeled issue automatically once work is explicitly multi-phase or an
  audit, expected to span sessions, or `TodoWrite`-worthy work that must survive a
  session boundary. Small single-turn/single-file work stays inline or in `TodoWrite`;
  a plan for a three-line fix is overhead, not diligence.
- Resuming cold: look for an in-progress plan on this objective (`todo_list` /
  `todo_context`, `label=plan`) and ask which to resume, or confirm starting fresh.
- Escalating to delegation (workers, model tiering, parallel runs): automatic when
  clearly warranted, a quick check-in when ambiguous, never silent. That settles the
  delegation decision only; "Working style"'s one-item-at-a-time rule still governs the
  substance of the work.
- Prefer a cheap fresh worker over a fork for bounded mechanical work the prompt can
  fully specify. A fork always runs on the orchestrator's model and only pays off when
  re-deriving context costs more than the price difference (the skill's Model Tiering
  section).
- If Dibs tooling itself misbehaves, report it with `todo_report_bug` rather than
  working around it silently.

**Shared knowledge:** `research` issues (checksum-versioned findings, reused until the
files they're based on change) and `lesson` issues (durable non-code gotchas: platform
quirks, library fine print, logic traps), under Personal Projects → AI workflows unless
project-specific. Check both before researching anything; whoever finds something
durable updates them, not just delegated workers.

**Token efficiency:** verify via diffs/status instead of re-reading files, grep/glob
before full reads, run tools with quiet flags and keep only pass/fail + errors in
checkpoint comments, batch independent steps, and `/clear` between unrelated phases once
state is in Dibs.

## Memory scope discipline

When Andres gives feedback or states a preference that's about general workflow,
tooling, or collaboration style — not tied to one specific project's code or business
logic — proactively point out that it looks global rather than project-specific, and
offer to save/update it here (or in the relevant shared skill file) in addition to or
instead of a project-scoped memory entry. Don't assume either way; ask. The goal is to
avoid a genuinely general rule getting buried in a single project's memory where other
projects never benefit from it.

## Comments

Default to no comments. When one is warranted (a non-obvious WHY, a hidden
constraint, a workaround for a specific bug), keep it concise and only about why the
code is the way it is — never a changelog of what was tried before, why it's no
longer relevant, who wrote it, or a reference to the task/fix that produced it.

## Label and tag names

Name labels, tags, categories and similar free-text identifiers with spaces, not hyphens
(`needs research`, not `needs-research`). GitHub labels, Dibs and most trackers accept spaces
fine, and a hyphen-versus-space mismatch makes exact-name filters silently return nothing.
Keep a hyphen only in a word that is genuinely hyphenated. Applies to any new label, including
ones code or docs create or refer to. Decided 2026-09-19 in the Dibs repo: the docs told agents
to filter by `agent-task` while the real label was `agent task`, so the filter matched nothing.

## Avoid over-engineering

Prefer the simplest design that addresses the real risk or requirement. When a fix starts
growing extra moving parts (new services, permission schemes, abstractions), stop and check
its value against the actual threat model or use case before building it, and say so if the
simpler option is good enough. Decided 2026-10-05 in Dibs: a dedicated container UID with ACLs
and an extra service was built to block same-UID `/proc` reads, but the read-write source bind
mount already gave a compromised web tier a path to the host user, so a configurable UID plus
a documented trust model was the right size.

## Avoid hardcoding

Prefer settings/config, environment variables, or language/translation files over
literals for anything that could plausibly be dynamic, change in the future, need to
differ per environment, or need to differ if the code is cloned/reused elsewhere (a
new site, a new client, a new deployment). This applies broadly: text/copy, magic
numbers/thresholds, credentials, URLs, IDs. Where a project has no ready mechanism
for a specific value (e.g. legacy code with no settings system for that spot), at
minimum extract it to a clearly-named constant/variable near its use rather than
leaving it as an inline literal — cheap now, and marks it for a future proper home
(env var, settings table, language file, etc.).

- **OpenCart projects:** the mechanism is usually a module's DB-backed settings
  (e.g. `theme_settings`) — see `opencart-legacy.md`.
- **Laravel projects:** `.env`/config files for environment-specific values,
  language files for user-facing text, DB-backed settings for anything
  admin-editable.

## Per-project CLAUDE.md maintenance

- Every project must have its own `CLAUDE.md` at the repo root documenting that
  project's rules, requirements, and architecture. If one is noticed missing while
  working in a project, proactively offer to create it (use the `init` skill).
- When creating one, don't rely on codebase analysis alone — ask the user directly
  about anything not confidently inferable from the code, to minimize assumptions
  and repeated questions in later sessions. At minimum cover:
  - Git workflow: branch model, remotes, whether it follows the standard
    master/local/feature pattern from this file or something project-specific.
  - Testing and linting: which tools (Pest, PHPUnit, Pint, PHPStan, Rector,
    ESLint, etc.), how they're actually run (host vs. container, exact commands),
    and which must pass before a commit is allowed.
  - How the project is served/run locally: Docker vs. host, container names,
    ports, `setup.sh`/`docker-compose.yml` presence, Traefik routing if used.
  - Anything else project-specific worth capturing to make future sessions
    smoother and more correct: production target (yes/no, for staleness rules),
    deploy process, any non-standard conventions.
- Keep it up to date in the same commit as the change it describes (see "Docs and
  tests travel with the change" below): once Andres has confirmed he wants a commit
  made, and before creating that commit, check whether the change is worth
  documenting there and update it if so.
- Minor/trivial changes don't need an entry in `CLAUDE.md`. Things that do:
  refactors, new routes/endpoints, architecture changes, new requirements or
  conventions. (This exemption covers `CLAUDE.md` only — a doc the change makes
  *wrong* must always be fixed in the same commit.)

## Docs and tests travel with the change

Documentation and tests for a change go in the **same commit** as the feature or
change itself — not a follow-up commit, not a later cleanup. This covers every doc a
project keeps, not just the obvious one: the project's `CLAUDE.md`, agent/skill/
instruction files (`.claude/project.md`, `SKILL.md`, `AGENTS.md`), README,
SECURITY/CONTRIBUTING, anything under `docs/`, and any bespoke project document.
Code, docs and tests should never be out of sync at any given commit, so every
commit stands on its own — reviewable, bisectable and revertable as one unit.

- **Say what the project is now.** Describe the change or new state, at the level of
  detail that suits that document (README: what a user sees or configures;
  `CLAUDE.md`/architecture docs: structure and conventions; a skill: how an agent
  should behave). Don't narrate the previous state — the exception is internal
  material where a lesson was learned, a decision was made, or a requirement changed;
  then record that lesson/decision/requirement and why.
- **Mention what's next or planned** when it's useful to a reader, and only what's
  actually planned. Don't document an unbuilt feature as if it exists.
- **Tests for the feature ride in the same commit**, happy and sad paths (see "Test
  coverage" above), not deferred.
- **Find every affected doc before committing**, not just the first one you think of:
  search the docs for the old tool/argument/config/command names the change touches,
  since a doc that contradicts the code is the usual miss.
- If a miss is found after a commit already exists, fix it in a follow-up docs commit
  and say so plainly as a miss; never rewrite a pushed commit to hide it (see the hard
  rules on history rewrites).

Decided 2026-09-21 in the Dibs repo: a commit changed MCP tool arguments and left
`skills/dibs/SKILL.md` still telling agents the old usage until a later fix.

## Feature atlas (feature/subsystem inventory)

Any project can opt into a maintained `.ai/feature-atlas/` inventory of its own
features/subsystems via `/feature-atlas` (see that command's own doc for the full
mechanism). Where it exists, it's the source of truth for feature boundaries,
interfaces, dependencies, and standing maintainability findings — read it before
re-deriving that from scratch by rescanning the codebase, and proactively suggest
re-running it if it looks stale relative to recent commits.

## Context window management

Every call re-reads the whole context, so a session's size matters well before the
window is full: cache reads were ~95% of all tokens in a week-long audit (2026-10-05),
with sessions running to ~950k. Budget: once context passes **~250k tokens**, tell
Andres and offer `/handoff` then `/clear` before starting new work (finish the current
step first). Same when coming back to a session idle longer than the prompt-cache TTL
(~1h) with a large context: the next prompt rewrites the whole context at cache-write
price, so a fresh session from a hand-off is usually cheaper. Avoid `/model` switches
and plugin reloads mid-way through a big session for the same reason (each forces a
full cache rewrite).

## Hooks summary (see hooks config for full detail)

**All projects:**
- Push guard (`hooks/push-guard.sh`, PreToolUse on Bash): any command containing
  `git push` (including `rtk git push` and chained commands) forces a permission prompt
  showing the exact command, whatever the permission mode or allow rules.
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

## On-demand context

Kept out of this file so it isn't loaded into every session; read the skill when it applies:

- C or C++ work, or code for embedded/SBC hardware (Raspberry Pi etc.) → `c-cpp` skill.
- Adding or changing anything under `~/dotfiles/ai/` (skills, commands, agents, hooks,
  settings) or opencode/Codex/agy config → `ai-config` skill.
- Skills, agents and commands are listed by each tool's own discovery, so there's no
  catalogue here.

@RTK.md
