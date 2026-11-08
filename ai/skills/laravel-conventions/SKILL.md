---
name: laravel-conventions
description: Laravel/Livewire conventions: thin controllers to actions to services, return values, transactions, strict typing, error handling, DB choice and N+1, Rector (dry-run only). Use when writing or reviewing Laravel code, DB code or Rector config.
---

# Laravel Conventions

Applies to all Laravel/Livewire projects (not OpenCart — see `opencart-legacy.md`).

## Architecture: thin controllers → actions → services

- **Controllers** (both web and API) handle request validation and call actions. They
  do not contain business logic.
- **Actions** are single-purpose, invokable classes with one public `handle()` method.
  This is where business logic lives.
- **Services** are called by actions when the work involves a third party or network
  call (external APIs, payment providers, queues to external systems, etc.). Actions
  don't talk to third parties directly — they delegate to a service.
- **Tests** should call and test actions directly, not just through HTTP/controller
  tests. Controller/feature tests can still exist for request validation and HTTP
  contract, but business logic correctness is verified at the action level.

## Action return values

Actions return the result of their work, typed appropriately to the operation:

- **Create/Update** → return the Eloquent model
- **Delete** → return `bool`
- **Custom actions** → return whatever's natural: a value object/DTO, array, string,
  or a simple success/failure indicator — whatever best represents the outcome of that
  specific action. Don't force a generic wrapper type if it doesn't fit.

## Jobs and commands

Laravel jobs (queued) and Artisan commands should also delegate their logic to action
classes rather than containing business logic inline — same pattern as controllers:
job/command handles the entry point and orchestration, the action does the work.

## Database transactions in actions

Actions that perform multiple related database writes should wrap them in a DB
transaction, so a partial failure doesn't leave inconsistent data. If a transaction
fails or rolls back, that should be reported/logged clearly (not silently swallowed) —
see the error handling section below for the expected-vs-real-exception distinction.

## Strict typing

- `declare(strict_types=1);` at the top of every file, where the PHP version in use
  supports it. Older PHP versions in legacy contexts may not — check project PHP
  version before assuming this applies.
- Always type-hint parameters and return types on action `handle()` methods, service
  methods, and anything else under your control.
- Prefer enums over string/int constants when the value set is fixed and meaningful
  (e.g. statuses, types). Define enums in a sensible, discoverable location — typically
  `app/Enums/`, not buried inside an unrelated class.

## Error handling

Distinguish between **expected** failure modes and **real** bugs:

- **Expected errors** — things that can legitimately happen in normal operation, like
  an unresponsive third-party API, malformed JSON from an external response, an
  authorization failure, a timeout — should be caught with try/catch in the
  action/service layer and handled gracefully (return a failure result, log it,
  whatever fits the action's return contract). These are not exceptional in the
  PHP-exception sense; they're expected outcomes that need handling.
- **Real exceptions** — genuinely unexpected conditions (a programming error, an
  invariant violation, something that should never happen if the code is correct)
  should be allowed to throw, especially in local/dev environments, so they surface
  and get fixed rather than being silently swallowed.

Don't wrap everything in a blanket try/catch "just in case" — that hides real bugs.
Be deliberate about what's expected-and-handled vs unexpected-and-should-throw.

## New projects

Default to the latest stable Laravel, Livewire and Flux for a new project, even when a spec or
prompt names an older major (for example "Livewire 3"); say so in the plan instead of asking. Pin an
older major only when Andres asks for it or an existing project requires it.

## Database

- Live ecommerce/work projects usually run MySQL/MariaDB, personal projects SQLite, with exceptions.
  Check the project's `.env`/config; when unclear in `/project-bootstrap`, ask.
- Be deliberate about eager loading (`with()`, `load()`) wherever a loop touches relationships (N+1).
- A driver-specific quirk (enums, JSON, full-text) is worth a quick check, not an assumption.

## Rector

Laravel projects with a `rector.php` only; OpenCart never, unless the project's `.claude/project.md` opts in.

- Always `--dry-run` first, show Andres the diff and wait; never auto-apply. The `rector-guard.sh` hook
  denies `rector process` / `composer rector:apply` without `--dry-run`, and the pre-commit hook blocks
  a commit when the dry-run finds changes.
- Run in the container: `docker exec <container> ./vendor/bin/rector process --dry-run` (or `composer rector`).
- Reference config `~/www/stocker/rector.php`: paths `app`, `database`, `routes`, `tests`; sets
  `LevelSetList::UP_TO_PHP_83` (match the project's PHP), `SetList::CODE_QUALITY`, `SetList::DEAD_CODE`;
  `importNames()`, `importShortClasses(false)`; skip `ClosureToArrowFunctionRector`.
- Avoid `SetList::STRICT_MODE` (unless PHPStan level 9+) and any run on OpenCart paths.
- After applying, re-run PHPStan at the project's level.
