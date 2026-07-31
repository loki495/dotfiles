# Pest Testing

Applies to Laravel projects (not OpenCart, unless a project explicitly opts in via its
own `.claude/project.md`).

## Syntax

- Pest syntax only — `it()`, `test()`, `describe()` blocks. Never PHPUnit class-based
  syntax in these projects.
- Group related tests with `describe()` blocks for readability.
- Use Pest's expectation API (`expect()`) rather than PHPUnit assertions.

## What to test

- Per `laravel-conventions.md`: business logic correctness is verified at the **action**
  level. Write unit/action tests that call `handle()` directly and assert on the
  returned result (model, bool, DTO, whatever the action returns).
- Feature/HTTP tests still have a place for verifying request validation, route
  behavior, and the HTTP contract — they're not redundant with action tests, they
  cover a different layer.
- Mock third-party/network calls with `Http::fake()` (or the relevant fake) rather than
  hitting real external services in tests.

## Database

- Use `RefreshDatabase` trait on feature tests that touch the database.
- Be aware of the project's DB driver (MySQL vs SQLite — see `db-context.md`). SQLite
  in-memory is common for fast local test runs; confirm which a given project uses
  before assuming behavior that differs between drivers (e.g. certain SQL features).

## Factories

- Prefer factory states over raw arrays when building test data.

## Test design principles (apply beyond Pest too, e.g. bespoke OpenCart harnesses)

- Prefer smaller, stateless tests (a single invariant, no shared setup) over larger
  stateful ones when they prove the same thing — but stateful integration/feature
  tests are fine when that's the deliberate point of the test; just be purposeful
  about it and know what side effects it causes.
- Prefer a simple, stateless, code-level invariant over a stateful safety mechanism
  (tokens, rotation, cache files, DB-seeded flags) for things like "route this test
  to sandbox mode" — e.g. a reserved-TLD email (`*@*.invalid`) routing to a sandbox
  API key, rather than a generated/rotated test token — when such an invariant
  exists or can reasonably be added.
- When seeding test data, prefer fresh randomized data each run with expected values
  *derived* from what was just seeded, over fixed "golden" fixture numbers — this
  verifies the logic holds for arbitrary inputs, not just memorized ones. A simpler
  stateless assertion is fine too when it proves the same thing with equal certainty.

## Testing against real third-party APIs

- Fake/mock third-party calls (`Http::fake()` or equivalent) unless hitting the real
  API is actually necessary to prove something a fake can't.
- When a real hit is necessary, prefer the provider's sandbox credentials/endpoint/
  test-mode flag if one exists.
- If no sandbox exists, make the test idempotent and minimize the real-world surface
  area: don't spam real emails/SMS, don't charge real cards, mark any created records
  (orders, accounts) as test data obviously, and never consume paid credits or incur
  charges unnecessarily.
- Trade-off to stay aware of: mocking a third-party API means a real change to that
  API's response shape won't be caught by the suite and could silently break
  production. Not a reason to avoid mocking, just worth noting near the mock (or as
  an occasional real-hit smoke test) when the risk seems worth guarding against.

## Hard rule: tests are not to be touched to force a pass

This is a hard rule, not a style preference:

- Tests must never be **deleted**, have their **assertions weakened**, or be
  **skipped/marked incomplete** in order to make a failing suite pass — without Andres's
  explicit confirmation first.
- If a test fails, the default action is to investigate and fix the underlying code,
  or flag the conflict clearly and ask how to proceed. Editing the test to match
  broken behavior is not an acceptable shortcut.
- This applies whether you're working interactively or as part of the pre-commit hook
  flow — if Pest fails at commit time, fix the code or stop and ask; don't touch the
  test to get a green checkmark.
