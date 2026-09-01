# Global Developer Context — Andres

This file applies to all Claude Code sessions on this machine, regardless of project.

## Hard rules — always / never

- **NEVER** push to any remote without stating the exact branch + remote first and
  getting explicit confirmation.
- **NEVER** force-push, or rewrite a commit already pushed to a shared remote,
  without explicit confirmation — even if rewriting the commit itself was approved.
- **NEVER** delete, weaken, or skip/bypass a test to force a passing state without
  explicit confirmation from Andres first.
- **NEVER** take a real-world-visible action (a real email/SMS, charging a card, a
  third-party write endpoint, a user-visible notification) without confirming first —
  applies even inside test code or a one-off script. When in doubt whether something
  counts, ask.
- **ALWAYS** ask rather than assume when project type, branch/worktree layout, or
  intent is ambiguous.
- **ALWAYS** work one item at a time on multi-issue/audit work — explain, present
  options, get a decision — before implementing the next one. (Repetitive mechanical
  steps within an already-agreed plan are exempt — see "Working style".)

## Machine layout

- All projects live under `~/www/`. No naming convention — folder names are freeform,
  and for live (non-personal) projects the domain name may appear somewhere in the path.
- Some projects use git worktrees for parallel branch work (e.g. `client-b`,
  `client-a`). Worktree structure varies per project and is NOT assumed.
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

## C/C++ development

- Andres knows both C and C++, but his background is pre-2000s style. Expect
  him to ask about modern idioms/standards (C99/C11/C17, C++11 and later —
  RAII, smart pointers, `<functional>`/lambdas, move semantics, etc.) rather
  than assume familiarity — explain briefly when introducing them instead of
  using them silently.
- For a project targeting embedded/SBC hardware (e.g. Raspberry Pi GPIO
  work) where code must actually build and run on the target device: prefer
  two independent **non-bare** git repos (dev machine + device), synced by
  direct `git push` to the device with `receive.denyCurrentBranch =
  updateInstead` set on the device repo (push updates its working tree
  directly, no separate pull step) — plus a small local wrapper script that
  pushes, then builds and runs over ssh on the device, streaming output back.
  Confirmed working well for `Ws2818` (Raspberry Pi + WS281x LED strip); no
  GitHub/hosted remote or full local/feature branch model needed for this
  kind of single-developer, single-target project — that heavier model is
  for projects with a real shared/production remote.

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
- For multi-session/phased work (a plan doc, a numbered set of phases, a long todo
  list tackled incrementally), proactively offer a ready-to-paste hand-off prompt
  for the next session — but only when it's actually warranted: context is getting
  full, or a fresh session is genuinely needed to avoid missing info/hallucination
  from an overloaded context. Don't offer this reflexively after every small chunk
  of finished work.
- When a message is phrased as "Todo: ...", "next: ...", or "after [current thing],
  do ...", treat it as a backlog note, not a request to context-switch immediately —
  add it to the project's `todo` file and keep working the current item(s). Only
  implement it right away if explicitly told to do so now ("do this now", "right
  now", "go ahead and do it", etc.). Plain direct statements without that deferral
  framing ("X should show Y", "the page doesn't have Z") are normal requests, not
  backlog notes — implement those as usual.

## Multi-step work: plans, research, lessons (default workflow)

For any multi-step coding work — refactors, audits, multi-file features, anything
likely to span more than one sitting — the `orchestrator-worker` skill's file-based
protocol is the **default**, not something to invoke on request. Read that skill for
full mechanics; summary of what it means day to day:

- **When a plan folder gets created:** automatically, without being asked, once a
  task is explicitly multi-phase/an audit, expected to span sessions, or is
  `TodoWrite`-worthy work that needs to survive a session boundary. Small
  single-turn/single-file work stays inline or as a plain `TodoWrite` list — no
  folder needed, and creating one for a three-line fix is overhead, not diligence.
- **Where it lives:** `.ai/plans/<plan-slug>/` at the project root — one folder per
  initiative, agent-agnostic (readable/writable by Claude Code, opencode, Codex, or
  agy, not Claude-specific), with `.ai/plans/INDEX.md` as the registry of
  active/paused/done work.
- **Resuming cold:** at the start of work in a project that has `.ai/plans/`, check
  `INDEX.md` for in-progress plans before starting new multi-step work, and ask which
  to resume (or confirm starting fresh) rather than assuming.
- **Escalating to full delegation** (spawning workers, model tiering, parallel
  execution): automatic once it's clearly warranted, or a quick check-in when it's
  ambiguous — never silently. This satisfies the "work one item at a time, get a
  decision before the next" rule in "Working style" above for the *delegation*
  decision specifically; it doesn't replace that rule for the substance of the work.
- **Shared, cross-plan knowledge:** `.ai/research/` (checksum-versioned investigative
  findings, code-specific or general — reused until the files they're based on
  change) and `.ai/lessons/` (durable non-code-specific gotchas — platform quirks,
  library fine print, logic traps) live outside any single plan folder. Check both
  before researching anything; update both after finding something durable, by
  whoever did the step, not just delegated workers.
- **Token efficiency is part of the default, not an afterthought:** verify via
  diffs/status instead of re-reading full files, prefer targeted grep/glob over full
  reads, run lint/test/static-analysis tools with quiet flags and keep only
  pass/fail + errors in plan files (never raw verbose output), batch independent
  steps, and treat `/clear` between unrelated phases as safe and encouraged once a
  phase's state is persisted to the plan folder.

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
- Keep it up to date at commit time: once Andres has confirmed he wants a commit
  made, and before creating that commit, check whether the change is worth
  documenting there and update it if so.
- Minor/trivial changes don't need an entry. Things that do: refactors, new
  routes/endpoints, architecture changes, new requirements or conventions.

## Feature atlas (feature/subsystem inventory)

Any project can opt into a maintained `.ai/feature-atlas/` inventory of its own
features/subsystems via `/feature-atlas` (see that command's own doc for the full
mechanism). Where it exists, it's the source of truth for feature boundaries,
interfaces, dependencies, and standing maintainability findings — read it before
re-deriving that from scratch by rescanning the codebase, and proactively suggest
re-running it if it looks stale relative to recent commits.

## Context window management

When context is getting close to full, warn Andres proactively rather than letting
it auto-compress silently. Offer to write a hand-off prompt file capturing the
info/decisions agreed on so far in the session, ready to paste into a fresh session.

## Backlog files (todo / bugs.md)

- Most projects should keep an up-to-date `todo` file (and optionally a `bugs.md`) at
  the repo root for open and in-progress work. This is a different tool from
  `.ai/plans/` (see "Multi-step work" above): `todo`/`bugs.md` is a flat, repo-wide
  backlog of what's not started yet; `.ai/plans/<slug>/` is per-initiative, in-flight
  session state for something already underway. An item graduates from `todo` to its
  own plan folder once work actually begins on it, not before.
- These files track what's **left to do**, not a history log. When an item is
  completed, remove it rather than marking it done/fixed in place — don't leave a
  growing record of finished work in these files.
- If a completed item taught a real lesson (a gotcha, a wrong assumption worth
  remembering), capture that in the relevant place instead — a concise code comment
  only if the WHY is non-obvious, project docs, or CLAUDE.md/project.md — not as a
  "done" note left behind in the todo/bugs file.
- **Global `Todo:` handling (Andres 2026-08-25):** when Andres says `Todo:` or
  `add to Todo:` (or similar), read the local `todo` file first to see its
  format, append the mentioned item wherever is most appropriate in that file's
  existing structure, then continue with whatever was being done — don't treat
  it as a context-switch request. Plain direct statements without `Todo:` deferral
  framing remain normal requests to implement immediately.

## Hooks summary (see hooks config for full detail)

**Laravel projects:**
- On PHP file write: Pint (auto-fix) → PHPStan level 6 (report only, must address before commit)
- Pre-commit: Pint (auto-fix, re-stage) → PHPStan level 6 (blocks on failure) → Rector
  dry-run (blocks if changes found, shows diff, never auto-applies) → Pest (blocks on
  failure; see hard rule above)

**OpenCart projects:**
- No automatic hooks. Opt-in only via project's own `.claude/project.md`.

## Skills available

`laravel-conventions`, `livewire-components`, `pest-testing`,
`opencart-legacy`, `frontend-stack`, `db-context`, `git-workflow`, `rector`,
`backup-setup`, `verifying-identity`, `resource-cleanup`, `orchestrator-worker`,
`ac495-infrastructure`

## Agents available

- **Core:** `code-reviewer` (dual ruleset: Laravel strict / OpenCart safe), `git-helper`
  (push-safety + branch model enforcement), `legacy-auditor` (OpenCart read-only scanner),
  `test-writer` (Pest only, subagent)
- **Feature atlas family:** `feature-atlas-mapper` (whole-repo subsystem-boundary
  discovery), `feature-atlas-scout` (per-subsystem deep static analysis),
  `feature-atlas-auditor` (per-subsystem maintainability audit),
  `feature-atlas-synthesizer` (cross-subsystem validation + report)

## Commands available

`/project-bootstrap` — detects project type, checks/offers to install tooling, scans
existing `~/www/` docker-compose patterns to generate new project docker-compose +
Traefik config + setup.sh, adds composer script wrappers, writes `.claude/project.md`
when worktree/branch structure is ambiguous.

`/feature-atlas` — discovers and audits every feature/subsystem in the current project
(frontend + backend), writing `.ai/feature-atlas/` as the project's source of truth for its
feature inventory and standing maintainability findings. Re-runnable; only refreshes what
changed. See "Feature atlas" section above.

`/feature-atlas-subsystem <name>` — refreshes one subsystem's entry cheaply, without rescanning
the whole codebase.

`/feature-atlas-report` — re-validates and re-ranks findings from existing subsystem audits into
`REPORT.md`, without rescanning any code.

## opencode restart requirement

opencode loads its config, agents, commands, skills, and plugins **once when it starts** — it is
not hot-reloaded. After any of these change, the **opencode serve process must be restarted**
(quit and relaunch opencode entirely; closing/reopening an individual session is NOT enough, the
running server keeps the already-loaded config):

- `opencode.json` / `opencode.jsonc` (any field)
- `~/.config/opencode/agent(s)/` — agent files
- `~/.config/opencode/command(s)/` — command files
- `~/.config/opencode/skill(s)/<name>/SKILL.md` — skill definitions
- `~/.config/opencode/plugin(s)/` or any `plugin:` listed JS/TS plugin
- any file referenced by `instructions` (e.g. `~/.claude/CLAUDE.md`) that changes system context

@RTK.md
