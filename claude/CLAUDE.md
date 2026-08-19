# Global Developer Context — Andres

This file applies to all Claude Code sessions on this machine, regardless of project.

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

Rules:
- If only one thing is being worked on at a time, work happens directly on `local`.
- If multiple things are in flight, create a feature branch off `local` named for the feature.
- Cherry-picks intended for production go to `master`/`main`/`stable` first, then are
  rebased up through `local` → any feature branches.
- Local-only changes (config tweaks, debug code, experiments) live only on `local` or
  feature branches — never on `master`/`main`/`stable`.
- Remote is usually `origin`. Some projects use `upstream` for the canonical/production
  remote when `origin` points to a personal fork (e.g. GitHub mirror).
- **Never push without explicit confirmation.** Always state which branch and remote
  before pushing, and flag if a push target looks like it would put local-only work
  somewhere it shouldn't be.
- While a commit is still local-only (not yet cherry-picked/pushed to
  master/main/stable), prefer amending it over stacking new small commits for
  follow-up tweaks/fixes to the same feature — keeps local-only history clean
  before it ships. Once a commit has been cherry-picked/pushed to a
  production-mirror branch, never amend it — start a new commit instead. Use
  judgment on "same feature": a genuinely separate fix or unrelated change still
  gets its own commit.
- No existing git hooks (husky etc.) are in use unless a project says otherwise.

See `git-workflow.md` skill for cherry-pick/rebase details and the `git-helper` agent
for push-safety checks.

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

## External side effects

Confirm before any action that could have a real-world, externally-visible effect:
sending a real email/SMS, charging a card, calling a write endpoint on a third-party
API, or triggering a notification a real user would see — whether it's test code, a
one-off script, or a manual fix. When in doubt whether an action is real-world-
visible, ask before running it.

## Verifying identity, not just success

A successful, plausible-looking response (a valid API token, real-looking data, a
"200 OK") is not proof you're talking to the *correct* account, environment, or
tenant — only that the credentials/config work for *some* account. This matters most
when there's known history of multiple accounts/environments (old vs. new, staging
vs. prod, a prior attempt at the same integration).

Before declaring credentials/config "verified":
- Where possible, self-verify rather than only asking the user to check manually:
  ask the user for one or more identifying facts you can independently confirm via
  the API (e.g. "what email is on this account?", "how many products are in
  category X?"), then query the API for that same field and compare. If it doesn't
  match, treat the credentials/environment as wrong until proven otherwise — don't
  proceed as if verified.
- If self-verification isn't possible (no distinguishing field available via the
  API), ask the user to confirm independently from a source that can only show the
  true target — their own logged-in dashboard/app — rather than running more API
  calls against the same possibly-wrong credentials.

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

## Scratch scripts and fixed/reused resource paths

Any script — a one-off scratch/dev-server helper, or real project tooling —
that binds to a **fixed, reused** resource path (a Unix socket, a lock
file, a PID file) must find and terminate whatever process is already
holding that resource *before* it unlinks/rebinds it, as the very first
thing it does. Don't rely on a separate "remember to clean up when you're
done" step, manual or otherwise — a session can end abruptly (context
limit, crash, dropped connection, SIGKILL) before any end-of-run cleanup
step ever executes, so a "clean up at the end" habit alone is unreliable
by construction.

Prefer a unique resource path per invocation (timestamp/PID-suffixed) when
that's easy — then there's nothing to orphan in the first place. When a
fixed/reused path is unavoidable or already an established convention, add
the self-cleaning step at start instead.

Found live 2026-08-08 (claude-session-manager): a test/dev-server harness
script only ever unlinked a socket *file* before rebinding, never the
*process* still holding the old listener open — ten orphaned instances had
piled up silently over several days. Matching an AF_UNIX socket back to
its owning process needs `/proc/net/unix` (maps a bound path to the
socket's real kernel inode) cross-referenced against `/proc/*/fd/*` -
**not** `fileinode()`/`stat()` on the socket file, which is a completely
different, unrelated number space and will silently match nothing.

## Tests — hard rule

Tests must never be deleted, modified to weaken assertions, or skipped/bypassed in order
to force a passing state — in hooks, in agents, or in normal conversation — without
explicit confirmation from Andres first. If a test fails, the default action is to fix
the underlying code or flag the conflict, not to alter the test.

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

## Context window management

When context is getting close to full, warn Andres proactively rather than letting
it auto-compress silently. Offer to write a hand-off prompt file capturing the
info/decisions agreed on so far in the session, ready to paste into a fresh session.

## Backlog files (todo / bugs.md)

- Most projects should keep an up-to-date `todo` file (and optionally a `bugs.md`) at
  the repo root for open and in-progress work.
- These files track what's **left to do**, not a history log. When an item is
  completed, remove it rather than marking it done/fixed in place — don't leave a
  growing record of finished work in these files.
- If a completed item taught a real lesson (a gotcha, a wrong assumption worth
  remembering), capture that in the relevant place instead — a concise code comment
  only if the WHY is non-obvious, project docs, or CLAUDE.md/project.md — not as a
  "done" note left behind in the todo/bugs file.

## Hooks summary (see hooks config for full detail)

**Laravel projects:**
- On PHP file write: Pint (auto-fix) → PHPStan level 6 (report only, must address before commit)
- Pre-commit: Pint (auto-fix, re-stage) → PHPStan level 6 (blocks on failure) → Rector
  dry-run (blocks if changes found, shows diff, never auto-applies) → Pest (blocks on
  failure; see hard rule above)

**OpenCart projects:**
- No automatic hooks. Opt-in only via project's own `.claude/project.md`.

## Skills available

`laravel-conventions.md`, `livewire-components.md`, `pest-testing.md`,
`opencart-legacy.md`, `frontend-stack.md`, `db-context.md`, `git-workflow.md`, `rector.md`,
`backup-setup.md`

## Agents available

`code-reviewer` (dual ruleset: Laravel strict / OpenCart safe), `git-helper`
(push-safety + branch model enforcement), `legacy-auditor` (OpenCart read-only scanner),
`test-writer` (Pest only, subagent)

## Commands available

`/project-bootstrap` — detects project type, checks/offers to install tooling, scans
existing `~/www/` docker-compose patterns to generate new project docker-compose +
Traefik config + setup.sh, adds composer script wrappers, writes `.claude/project.md`
when worktree/branch structure is ambiguous.

@RTK.md
