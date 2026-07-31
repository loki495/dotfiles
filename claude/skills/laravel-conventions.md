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
